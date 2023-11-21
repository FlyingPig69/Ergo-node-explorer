from flask import Flask, render_template, request, redirect, url_for
import requests
import json

app = Flask(__name__)

# Define the base URL
base_url= 'http://213.239.193.208:9053'
flask_url = 'https://ergo-node-explorer.vercel.app'

# Define specific paths
transaction_path = '/blockchain/transaction/'
token_path = '/blockchain/token/'
address_path = '/blockchain/transaction/byAddress/'
box_path = '/blockchain/box/'
info_path ='/info'

def get_url(endpoint):
    return base_url + endpoint

def get_token_name(token_id):
    token_data = {'name': 'Unknown', 'decimals': 0,'description': 'Unknown'}  # Initialize with default values
    token_response = requests.get(get_url(f"{token_path}byId/{token_id}"))
    if token_response.status_code == 200:
        token_data = token_response.json()
    return token_data.get('name', 'Unknown'), token_data.get('decimals', 0),token_data.get('description')

def process_transaction(transaction_id):
    transaction_url = get_url(f"{transaction_path}byId/{transaction_id}")
    transaction_response = requests.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()

        def process_assets(assets):
            asset_details = []
            for asset in assets:
                token_name, decimals,description = get_token_name(asset['tokenId'])
                amount = asset.get('amount', 0) / (10 ** decimals)
                asset_details.append({
                    'token_id': asset['tokenId'],
                    'token_name': token_name,
                    'amount': amount
                })
            return asset_details

        def process_input_output_data(data, data_type):
            details = []
            for data_item in transaction_data.get(data_type, []):
                assets = data_item.get('assets', [])
                item_details = {
                    'address': data_item['address'],
                    'value': round(data_item['value'] / 1000000000, 4),
                    'assets': process_assets(assets)
                }
                details.append(item_details)
            return details

        input_details = process_input_output_data('inputs', 'inputs')
        output_details = process_input_output_data('outputs', 'outputs')

        return {
            'Transaction ID': transaction_id,
            'Inclusion Height': transaction_data.get('inclusionHeight', ''),
            'Input Details': input_details,
            'Output Details': output_details
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
    #print("info is",info_url)

    return render_template('index.html', info_data=info_data, url=info_url,flask_url=flask_url)


@app.route('/transaction_details/<transaction_id>')
def transaction_details(transaction_id):
    transaction_data = process_transaction(transaction_id)

    if transaction_data:
        return render_template('transactions.html', transaction_details={transaction_id: transaction_data},flask_url=flask_url)
    else:
        return "Failed to retrieve transaction details."

@app.route('/process_box/<box_id>')
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
        print("Asset details:",asset_details)
        box_json=json.dumps(box_data, indent=4)

        if box_data:
            return render_template('box.html', box_data=box_data, asset_details=asset_details, box_json=box_json, url=url,flask_url=flask_url)

    except Exception as e:
        error_message = "An error occurred: {}".format(e)
        return render_template('error_template.html', error_message=error_message)

@app.route('/')
def process_box(box_id):

    transaction_url = get_url(f"{box_path}byId/{box_id}")
    transaction_response = requests.get(transaction_url)

    if transaction_response.status_code == 200:
        transaction_data = transaction_response.json()
        return (transaction_data, transaction_url)

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
        elif search_type == 'token_id':
            try:
                return "Search by Token ID: " + search_text
            except TypeError as e:
                error_message = "An error occurred: {}".format(e)
                return render_template('error_template.html', error_message=error_message)




if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, threaded=True)
