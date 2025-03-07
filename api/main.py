from flask import Flask, render_template, request, redirect, url_for
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
from datetime import datetime
import json
import time

retry_strategy = Retry(
    total=5,  # Max retries
    backoff_factor=5,  # Wait time: 5s, 10s, 20s, etc. (exponential backoff)
    status_forcelist=[500, 502, 503, 504],  # Retry only on these HTTP errors
    allowed_methods=["GET", "POST"]  # Which HTTP methods to retry
)
session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

app = Flask(__name__)

#todo Add unconfirmed

# Define the base URL
base_url= 'http://213.239.193.208:9053'
flask_url = 'https://ergo-node-explorer.vercel.app'

# Define specific paths
transaction_path = '/blockchain/transaction/'
transaction_u_path= '/transactions/unconfirmed/byTransactionId/'
token_path = '/blockchain/token/'
token_u_path ='/blockchain/box/unspent/byTokenId/'
address_path = '/blockchain/balance'
info_path = '/info'

box_path = '/blockchain/box/'
indexed_path='/blockchain/indexedHeight'
info_path ='/info'
block_path = '/blocks/'

headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
}

def get_url(endpoint):
    return base_url + endpoint

def get_token_name(token_id):
    token_data = {'name': 'Unknown','description': 'Unknown'}  # Initialize with default values
    token_response = session.get(get_url(f"{token_path}byId/{token_id}"))
    if token_response.status_code == 200:
        token_data = token_response.json()
    return token_data.get('name', 'Unknown'), token_data.get('decimals'),token_data.get('description')

def process_transaction(transaction_id): #process transaction and split into input/output list
    transaction_url = get_url(f"{transaction_path}byId/{transaction_id}")
    transaction_response = session.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()
        token_ids_to_check = [] #initialize tokens to check for delta
        def process_assets(assets):
            asset_details = []
            for asset in assets:
                token_name, decimals,description = get_token_name(asset['tokenId'])
                amount = asset.get('amount')
                token_ids_to_check.append(asset['tokenId'])
                asset_details.append({
                    'token_id': asset['tokenId'],
                    'token_name': token_name,
                    'amount': amount,
                    'decimals': decimals
                })
            return asset_details

        def process_input_output_data(data, data_type):
            details = []
            for data_item in transaction_data.get(data_type, []):
                assets = data_item.get('assets', [])
                item_details = {
                    'address': data_item['address'],
                    'value': round(data_item['value'] / 1000000000, 4),
                    'assets': process_assets(assets),
                    'box_id': data_item['boxId']
                }
                details.append(item_details)
            return details

        input_details = process_input_output_data('inputs', 'inputs')
        output_details = process_input_output_data('outputs', 'outputs')

        delta_result = calculate_delta(input_details, output_details)

        return {
            'Transaction ID': transaction_id,
            'inclusionHeight': transaction_data.get('inclusionHeight', 'inclusionHeight'),
            'creationHeight': transaction_data["outputs"][0]["creationHeight"],
            'Input Details': input_details,
            'Output Details': output_details,
            'delta': delta_result,
            'tx_json': transaction_data
        }
    else:
        return None

def process_transaction(transaction_id): #process transaction and split into input/output list
    transaction_url = get_url(f"{transaction_path}byId/{transaction_id}")
    transaction_response = session.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()
        token_ids_to_check = [] #initialize tokens to check for delta
        def process_assets(assets):
            asset_details = []
            for asset in assets:
                token_name, decimals,description = get_token_name(asset['tokenId'])
                amount = asset.get('amount')
                token_ids_to_check.append(asset['tokenId'])
                asset_details.append({
                    'token_id': asset['tokenId'],
                    'token_name': token_name,
                    'amount': amount,
                    'decimals': decimals
                })
            return asset_details

        def process_input_output_data(data, data_type):
            details = []
            for data_item in transaction_data.get(data_type, []):
                assets = data_item.get('assets', [])
                item_details = {
                    'address': data_item['address'],
                    'value': round(data_item['value'] / 1000000000, 4),
                    'assets': process_assets(assets),
                    'box_id': data_item['boxId']
                }
                details.append(item_details)
            return details

        input_details = process_input_output_data('inputs', 'inputs')
        output_details = process_input_output_data('outputs', 'outputs')

        delta_result = calculate_delta(input_details, output_details)

        return {
            'Transaction ID': transaction_id,
            'inclusionHeight': transaction_data.get('inclusionHeight', 'inclusionHeight'),
            'creationHeight': transaction_data["outputs"][0]["creationHeight"],
            'Input Details': input_details,
            'Output Details': output_details,
            'delta': delta_result,
            'tx_json': transaction_data
        }
    else:
        return None

def process_address_transaction(transaction_data): #process transaction for an address and split into input/output list

    token_ids_to_check = [] #initialize tokens to check for delta
    def process_assets(assets):
        asset_details = []
        for asset in assets:
            token_name, decimals,description = get_token_name(asset['tokenId'])
            amount = asset.get('amount')
            token_ids_to_check.append(asset['tokenId'])
            asset_details.append({
                'token_id': asset['tokenId'],
                'token_name': token_name,
                'amount': amount,
                'decimals': decimals
            })
        return asset_details

    def process_input_output_data(data, data_type):
        details = []
        for data_item in transaction_data.get(data_type, []):
            assets = data_item.get('assets', [])
            item_details = {
                'address': data_item['address'],
                'value': round(data_item['value'] / 1000000000, 4),
                'assets': process_assets(assets),
                'box_id': data_item['boxId']
            }
            details.append(item_details)
        return details

    input_details = process_input_output_data('inputs', 'inputs')
    output_details = process_input_output_data('outputs', 'outputs')

    delta_result = calculate_delta(input_details, output_details)

    return {
        'inclusionHeight': transaction_data.get('inclusionHeight', 'inclusionHeight'),
        'creationHeight': transaction_data["outputs"][0]["creationHeight"],
        'Input Details': input_details,
        'Output Details': output_details,
        'delta': delta_result,
        'tx_json': transaction_data
    }

@app.route('/')
def index():
    # Redirect to the index.html page
    info_url = get_url(f"{info_path}")
    info = session.get(info_url)
    print("info url", info_url)
    if info.status_code == 200:
        info_data = info.json()

    #get indexed status
    indexed_url = get_url(f"{indexed_path}")

    indexed = session.get(indexed_url)
    if indexed.status_code == 200:
        indexed_data = indexed.json()

    indexed_height=indexed_data['indexedHeight']
    print("indexed URL:",indexed_url,"  Indexed heigh",indexed_height)

    header_id = []
    no_txs = []
    height=[]
    timestamp=[]

    for i in range(5):
        result_header_id, result_no_txs = block2header(info_data['fullHeight']-i)
        height.append(info_data['fullHeight']-i)
        header_id.append(result_header_id)
        no_txs.append(result_no_txs)
        # get header timestamp from header info, need to loop this eventually
        header_url = get_url(f"{block_path}{header_id[i]}/header")

        header_response = session.get(header_url)
        if header_response.status_code == 200:
            header_data = header_response.json()
            timestamp.append(header_data['timestamp'])

    return render_template('index.html', info_data=info_data, url=info_url,flask_url=flask_url,base_url=base_url, header_id=header_id,no_txs=no_txs,height=height,timestamp=timestamp,indexed_height=indexed_height)


@app.route('/transactions/<transaction_id>') #render tranaction page
def transaction_details(transaction_id):
    transaction_data = process_transaction(transaction_id)

    if transaction_data:
        return render_template('transactions.html', transaction_details={transaction_id: transaction_data}, flask_url=flask_url)
    else:
        return "Failed to retrieve transaction details."


def block2header(block_height):

    block_url = get_url(f"{block_path}at/{block_height}")
    print("block url",block_url)

    header_id = session.get(block_url)
    if header_id.status_code == 200:
        header_id = header_id.json()

    header_id=header_id[0]
    #get number of transactions
    transaction_url = get_url(f"{block_path}{header_id}")
    transaction_response = session.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

    no_txs = len(transaction_data['blockTransactions']['transactions'])

    return (header_id,no_txs)


def process_box(box_id):

    transaction_url = get_url(f"{box_path}byId/{box_id}")

    transaction_response = session.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()
        return (transaction_data, transaction_url)


@app.route('/boxid/<box_id>')
def box_details(box_id):
    try:
        box_data,url = process_box(box_id)
        asset_details = []
        for asset in box_data['assets']:
            token_name, decimals, description = get_token_name(asset['tokenId'])
            if token_name != 'Unknown':
                amount = asset.get('amount') / (10 ** decimals)
                asset_details.append({
                    'token_id': asset['tokenId'],
                    'token_name': token_name,
                    'amount': amount,
                    'description': description
            })

        box_json=json.dumps(box_data, indent=4)

        if box_data:
            return render_template('box.html', box_data=box_data, asset_details=asset_details, box_json=box_json, url=url, flask_url=flask_url)

    except Exception as e:
        error_message = "An error occurred: {}".format(e)
        return render_template('error_template.html', error_message=error_message)

@app.route('/blocks/<header>')
def blocks_details(header):

    #get transactions in block/header
    transaction_url = get_url(f"{block_path}{header}")

    transaction_response = session.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

    #get header timestamp from header info, need to loop this eventually
    header_url = get_url(f"{block_path}{header}/header")

    header_response = session.get(header_url)
    if header_response.status_code == 200:
        header_data = header_response.json()

    #get timestamp and convert to text
    timestamp=header_data['timestamp']

    no_txs = len(transaction_data['blockTransactions']['transactions'])
    transaction_ids = [transaction['id'] for transaction in transaction_data['blockTransactions']['transactions']]
    transaction_details = []

    for i in transaction_ids:
        process_tx = process_transaction(i);
        transaction_details.append(process_tx)

    value = []
    for transaction in transaction_data['blockTransactions']['transactions']:
        total_value = sum(output['value'] for output in transaction['outputs'])
        value.append(total_value)

    if transaction_data:
        return render_template('blocks.html', transaction_details=transaction_details, flask_url=flask_url,header_data=header_data,no_txs=no_txs,value=value, timestamp=timestamp)
    else:
        return "Failed to retrieve transaction details."


@app.route('/search', methods=['GET', 'POST'])
def search_transaction():

    search_text = request.args.get('search_text')
    search_type = request.args.get('search_type')

    if search_text and search_type:
        if search_type == 'transaction_id':
            try:
                return redirect(url_for('transaction_details', transaction_id=search_text))
            except TypeError as e:
                error_message = "An error occurred: {}".format(e)
                return render_template('error_template.html', error_message=error_message)
        elif search_type == 'box_id':
            try:
                return redirect(url_for('box_details', box_id=search_text))
            except TypeError as e:
                error_message = "An error occurred: {}".format(e)
                return render_template('error_template.html', error_message=error_message)
        elif search_type == 'address':
            try:
                return redirect(url_for('address_details', address=search_text))
            except TypeError as e:
                error_message = "An error occurred: {}".format(e)
                return render_template('error_template.html', error_message=error_message)
        elif search_type == 'token_id':
            try:
                return redirect(url_for('token_details', tokenid=search_text))
            except TypeError as e:
                error_message = "An error occurred: {}".format(e)
                return render_template('error_template.html', error_message=error_message)


@app.route('/address/<address>')
def address_details(address):

    offset = request.args.get('offset', default=0, type=int)

    #transactions = requests.post(base_url+transaction_path+f"byAddress?offset={offset}&limit=10", headers=headers, data=address)
    transactions = session.post(base_url + transaction_path + f"byAddress?offset={offset}&limit=10", headers=headers,
                                 data=address)
    transactions = transactions.json()
    #tx_ids = [item["id"] for item in transactions["items"]]
    #print("Tx:", tx_ids)

    transaction_details = []

    for i in transactions['items']:
        process_tx = process_address_transaction(i);
        transaction_details.append(process_tx)

    #data = requests.post(base_url+address_path, headers=headers, data=address)
    data = session.post(base_url + address_path, headers=headers, data=address)
    address_data=data.json()

    #get current block height
    info_url = get_url(f"{info_path}")

    print("info url", info_url)
    full_height = session.get(info_url)
    if full_height.status_code == 200:
        full_height = full_height.json()

    full_height = full_height['fullHeight']
    #print("Height:",full_height)
    if address_data:

        return render_template('address.html', full_height=full_height, address=address, address_data=address_data, transaction_details=transaction_details,flask_url=flask_url, offset=offset)
    else:
        return "Failed to retrieve transaction details."

#this calculated the delta for a transaction
def calculate_delta(input_details, output_details):
    # Create a defaultdict to store delta values by address
    delta_by_address = defaultdict(dict)

    # Combine input and output details into a single list
    all_details = input_details + output_details

    # Get unique addresses from both input and output details
    unique_addresses = set(detail['address'] for detail in all_details)

    for address in unique_addresses:
        # Get details for the address from both input and output
        address_details = [detail for detail in all_details if detail['address'] == address]

        # Sum up the input and output values for the address
        input_value = sum(detail['value'] for detail in address_details if detail in input_details)
        output_value = sum(detail['value'] for detail in address_details if detail in output_details)

        # Calculate the delta for the value (output minus input)
        delta_value = output_value - input_value

        # Store the delta for the value in the defaultdict
        delta_by_address[address]['value'] = delta_value

        # Create a defaultdict to store token amounts for the address
        token_amounts = defaultdict(float)

        # Iterate through details for the address
        for detail in address_details:
            assets = detail.get('assets', [])
            for asset in assets:
                token_id = asset['token_id']
                token_name = asset['token_name']
                decimals = asset['decimals']
                amount = asset['amount']

                # Subtract the amounts for each token in input
                if detail in input_details:
                    token_amounts[(token_id, token_name, decimals)] -= amount
                # Add the amounts for each token in output
                elif detail in output_details:
                    token_amounts[(token_id, token_name, decimals)] += amount

        # Iterate through unique token details
        for token_details, amount in token_amounts.items():
            token_id, token_name, decimals = token_details

            # Check if decimals is None or not a valid numeric value
            if decimals is None or not isinstance(decimals, (int, float)):
                print(f"Skipping entry with invalid decimals: {token_details}")
                continue

            # Adjust the amount based on the decimal value
            adjusted_amount = amount / 10 ** decimals

            # Exclude entries with an adjusted amount of 0
            if adjusted_amount != 0:
                # Store the delta in the defaultdict
                delta_by_address[address][(token_id, token_name, decimals)] = adjusted_amount

    return dict(delta_by_address)


@app.route('/token/<tokenid>')
def token_details(tokenid):
    offset = 0
    limit = 16384
    tokens_data = []  # Initialize an empty list to store the results
    while True:
        token_url = get_url(f"{token_u_path}{tokenid}?offset={offset}&limit={limit}")
        tokens = session.get(token_url)
        tokens_json = tokens.json()

        if tokens.status_code == 200:
            data = tokens_json

            # Assuming data is a list of dictionaries
            for item in data:
                # Access values in each dictionary
                value_of_key = item.get('key')  # Replace 'key' with the actual key in your data
                tokens_data.append(item)

            # Check if there are more items
            if len(data) < limit:
                break  # Break the loop if there are no more items

            offset += limit  # Increment the offset for the next iteration
        else:
            print(f"Error: {tokens.status_code}")
            break  # Break the loop in case of an error
    name, decimals, description = get_token_name(tokenid)
    decimals = 10 ** decimals
    grouped_data = defaultdict(int)

    for entry in tokens_data:
        for asset in entry.get("assets", []):
            if asset.get("tokenId") == tokenid:
                grouped_data[entry["address"]] += asset["amount"]/decimals

    # Sort the data by highest to lowest amount
    tokens_data = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)
    holders = len(tokens_data)
    # Print the sorted result

    if tokens:
        return render_template('token.html', tokens_data=tokens_data, name=name, decimals=decimals, description=description, holders=holders, flask_url=flask_url)
    else:
        return "Failed to retrieve transaction details."

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False, threaded=True)

