# Module 2 - Create a Cryptocurrency

# To be installed:
# python3 - venv venv (everything runs within this vitual env)
# Flask==0.12.2: pip install Flask==0.12.2
# Postman HTTP Client: https://www.getpostman.com/
# requests==2.18.4: pip install requests==2.18.4


# Importing the libraries
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Part 1 - Building a Blockchain

class Blockchain:

    def __init__(self):
        self.chain = [] #this is the list that will contain all the blocks
        self.transactions = [] #this is the list that contains the transaction BEFORE they are added to the block. it is essensial to create this before the create_block function as we will use the transactions into the block below
        self.create_block(proof = 1, previous_hash = '0') #two requirments: the proof and the revious hash, for genesis block those are 1 and 0
        self.nodes = set() #all the nodes are initialized as a set as opposed to a list (better!) only takes the key values

    def create_block(self, proof, previous_hash): #this method creates the block with the values below and adds it to the chain, also returns the block
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 "transactions": self.transactions}
        self.transactions = [] #after we add the transaction into the block we need to empty the list again         
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1] # index of -1 returns the last index, in this case last index of the chain is the last block

    def proof_of_work(self, previous_proof): #this is the function that checks that SHA256 gives the correct result below a treshhold
        new_proof = 1 #we start the wile loop from nonce 1
        check_proof = False #loop goes as long as this is false
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest() #encode() basically puts a "b" in front of the number and hexdigest() return an hexodecimal, remember to convert to string!
            if hash_operation[:4] == '0000': #this is the treshold 0000
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode() #we sort the block values with the json.dumps()
        return hashlib.sha256(encoded_block).hexdigest() #we return the hash of the block, to be used later
    
    def is_chain_valid(self, chain): #check the validity of the chain
        previous_block = chain[0] #start of the chain
        block_index = 1 #first block index
        while block_index < len(chain): #iterate through the whole chain
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount): #this creates a transaction btw sender and receiver with a certain amount specified
        self.transactions.append({
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        })

        previous_block = self.get_previous_block()
        return previous_block["index"] +1 #we take the last index block and add a +1 for the current block

    def add_node(self, address):
        parsed_url = urlparse(address) #ParseResult(scheme="http", netloc="127.0.0.1:5000", path="/" ...) parsed_url basically destructure a url 
        self.nodes.add(parsed_url.netloc) #we only need to add the netloc and this is enough to identify the node = parsed_url.netloc
    
    def replace_chain(self): #this is for consensus, longest chain wins
        network = self.nodes
        longest_chain = None #initialized as none since we have not scanned the network yet
        max_length = len(self.chain) #chain inside the blockchain variable __init__
        for node in network:
            response = requests.get(f"http://{node}/get_chain") #using the get() function from the requests library imported above, get() expects an address (http://port 5000) and the type of request in this case /get_chain created with app route
            if response.status_code == 200:
                length = response.json()["length"] #from get_chain() method
                chain = response.json()["chain"]
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain

        if longest_chain: #this means if longest_chain is not None
            self.chain = longest_chain
            return True
        return False


# Part 2 - Mining our Blockchain

# Creating a Web App with Flask
app = Flask(__name__) 

# Creating an address for the node on Port 5000
node_address = str(uuid4()).replace("-", "") #we convert the uuid4 into string then remove the dashes "-"

# Creating a Blockchain
blockchain = Blockchain()

# Mining a new block
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transaction(sender = node_address, receiver = "Picozzi", amount = 1) #this specifies the reward to the miner, the sender is the node itself, receiver is the miner and amount is the reward
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congratulations, you just mined a block!',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                "transactions": block["transactions"]}
    return jsonify(response), 200

# Getting the full Blockchain
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

# Checking if the Blockchain is valid
@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'All good. The Blockchain is valid.'}
    else:
        response = {'message': 'Houston, we have a problem. The Blockchain is not valid.'}
    return jsonify(response), 200

# Adding a new transaction to the blockchain
@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json() #this method from "request library" gets the JSON file in POSTMAN
    transaction_keys = ["sender", "receiver", "amount"]
    if not all(key in json for key in transaction_keys): #if all the keys in transaction_keys are not present in the json file
        return "Some elements of the transactions are missing!", 400 #Request Bad
    index = blockchain.add_transaction(json["sender"], json["receiver"], json["amount"]) #the add_transaction returns the index of the block and append the block to the chain
    response = {"message": f"This transaction will be added to block {index}"}
    return jsonify(response), 201 #Created status 201

# Part 3 - Decentralizing blockchain

# Connecting new nodes
@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = request.get_json() #this method from "request library" gets the JSON file in POSTMAN
    nodes = json.get("nodes") #this contains the adresses of the request
    if nodes is None:
        return "no node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {"message": "All the nodes are now connected. Picoin blockchain now contains the following nodes",
                "total_nodes": list(blockchain.nodes)
    }
    return jsonify(response), 201

# Replacing the chain by the longest chain if needed
@app.route('/replace_chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain() #this returns a bool true or false
    if is_chain_replaced:
        response = {'message': 'The node had a different chain. The chain has been replaced with the longest one.',
                    "new_chain": blockchain.chain
        }
    else:
        response = {'message': 'All good, this chain is the longest one.',
                    "current_chain": blockchain.chain
        }
    return jsonify(response), 200

# Running the app
app.run(host = '0.0.0.0', port = 5000)   
            
            