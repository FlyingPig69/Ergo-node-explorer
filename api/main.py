from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime
import json

app = Flask(__name__)

# Define the base URL
base_url = 'http://213.239.193.208:9053'
flask_url = 'https://ergo-node-explorer.vercel.app/'

# Define specific paths
transaction_path = '/blockchain/transaction/'
transaction_u_path= '/transactions/unconfirmed/byTransactionId/'
token_path = '/blockchain/token/'
address_path = '/blockchain/balance'

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
    token_response = requests.get(get_url(f"{token_path}byId/{token_id}"))
    if token_response.status_code == 200:
        token_data = token_response.json()
    return token_data.get('name', 'Unknown'), token_data.get('decimals'),token_data.get('description')

def process_transaction(transaction_id): #process transaction and split into input/output list
    transaction_url = get_url(f"{transaction_path}byId/{transaction_id}")
    transaction_response = requests.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

        def process_assets(assets):
            asset_details = []
            for asset in assets:
                token_name, decimals,description = get_token_name(asset['tokenId'])
                amount = asset.get('amount')
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

        return {
            'Transaction ID': transaction_id,
            'inclusionHeight': transaction_data.get('inclusionHeight', 'inclusionHeight'),
            'creationHeight': transaction_data["outputs"][0]["creationHeight"],
            'Input Details': input_details,
            'Output Details': output_details,
            'tx_json': transaction_data
        }
    else:
        return None

@app.route('/')
def index():
    # Redirect to the index.html page
    info_url = get_url(f"{info_path}")
    info = requests.get(info_url)
    if info.status_code == 200:
        info_data = info.json()

    #get indexed status
    indexed_url = get_url(f"{indexed_path}")
    indexed = requests.get(indexed_url)
    if indexed.status_code == 200:
        indexed_data = indexed.json()

    indexed_height=indexed_data['indexedHeight']

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
        header_response = requests.get(header_url)
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
    header_id = requests.get(block_url)
    if header_id.status_code == 200:
        header_id = header_id.json()

    header_id=header_id[0]
    #get number of transactions
    transaction_url = get_url(f"{block_path}{header_id}")
    transaction_response = requests.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

    no_txs = len(transaction_data['blockTransactions']['transactions'])

    return (header_id,no_txs)

@app.route('/')
def process_box(box_id):

    transaction_url = get_url(f"{box_path}byId/{box_id}")
    transaction_response = requests.get(transaction_url)

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
            amount = asset.get('amount', 0) / (10 ** decimals)
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
    transaction_response = requests.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

    #get header timestamp from header info, need to loop this eventually
    header_url = get_url(f"{block_path}{header}/header")
    header_response = requests.get(header_url)

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


@app.route('/address/<address>')
def address_details(address):
    print("it went here")

    data = requests.post(base_url+address_path, headers=headers, data=address)
    address_data=data.json()

    if address_data:

        return render_template('address.html', address=address, address_data=address_data, flask_url=flask_url)
    else:
        return "Failed to retrieve transaction details."

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False, threaded=True)
