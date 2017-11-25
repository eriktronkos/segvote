from flask import Flask
from flask import request
from subprocess import check_output
import json
import requests
import hashlib as hasher
import datetime as date
import copy
import os.path
import sys
import os


node = Flask(__name__)


# Define what a SegVote block is
class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.hash_block()

    def hash_block(self):
        sha = hasher.sha256()
        sha.update(str(self.index) + str(self.timestamp) + str(self.data) + str(self.previous_hash))
        return sha.hexdigest()


# Generate genesis block
def create_genesis_block():
    # Manually construct a block with
    # index zero and arbitrary previous hash
    return Block(0, date.datetime.now(), {
        "proof-of-work": 9,
        "transactions": None
    }, "0")


# A completely random address of the owner of this node
miner_address = "genesis-node"
# This node's blockchain copy
blockchain = []
blockchain.append(create_genesis_block())
# Store the transactions that
# this node has in a list
this_nodes_transactions = []
# Store the url data of every
# other node in the network
# so that we can communicate
# with them
peer_nodes = []
# A variable to deciding if we're mining or not
mining = True
#Cache list of 90 first char of 'from' that identify if voter has voted already
cache_alreadyvoted = []

@node.route('/txion', methods=['POST'])
def transaction():
    # On each new POST request,
    # we extract the transaction data
    os.chdir('/home/erikeft/PycharmProjects/SegVote')

    new_txion = request.get_json()
    fromfile = open('from', 'w+')
    fromfile.write(new_txion['from'])
    fromfile.close()
    checkfrom = check_output(['./urs', '-verify-text', 'votacao', '-sig', 'from','-keyring', 'pubkeyring.keys'])
    if (checkfrom.strip() != 'true'):
        return "\'From\' invalid"
    if (checkAlreadyVoted(new_txion['from'])):
        return "This person already voted"

    if not os.path.isfile('cand'+str(new_txion['id'])):
        return "\'To\' invalid"

    sigfile = open('sig-to', 'w+')
    sigfile.write(new_txion['to'])
    sigfile.close()
    checksig = check_output(['./urs', '-verify-text', 'cand'+str(new_txion['id']), '-sig', 'sig-to', '-keyring', 'pubkeyring.keys'])
    if (checksig.strip() != 'true'):
        return "\'Sig\' invalid"

    #./urs -verify-text votacao -sig sig-voto -keypair pair.key -keyring pubkeyring.keys
    # Then we add the transaction to our list
    this_nodes_transactions.append(new_txion)
    # Because the transaction was successfully
    # submitted, we log it to our console
    print "New transaction"
    print "FROM: {}".format(new_txion['from'].encode('ascii', 'replace'))
    print "TO: {}".format(new_txion['to'].encode('ascii', 'replace'))
    print "ID: {}".format(str(new_txion['id']).encode('ascii', 'replace'))
    #print "AMOUNT: {}\n".format(new_txion['amount'])
    # Then we let the client know it worked out
    return "Transaction submission successful\n"


@node.route('/blocks', methods=['GET'])
def get_blocks():
    chain_to_send = copy.deepcopy(blockchain)
    # Convert our blocks into dictionaries
    # so we can send them as json objects later
    for i in range(len(chain_to_send)):
        block = chain_to_send[i]
        block_index = str(block.index)
        block_timestamp = str(block.timestamp)
        block_data = str(block.data)
        block_hash = block.hash
        chain_to_send[i] = {
            "index": block_index,
            "timestamp": block_timestamp,
            "data": block_data,
            "hash": block_hash
        }
    chain_to_send = json.dumps(chain_to_send)
    return chain_to_send


def find_new_chains():
    # Get the blockchains of every
    # other node
    other_chains = []
    for node_url in peer_nodes:
        # Get their chains using a GET request
        block = requests.get(node_url + "/blocks").content
        # Convert the JSON object to a Python dictionary
        block = json.loads(block)
        # Add it to our list
        other_chains.append(block)
    return other_chains


def consensus():
    # Get the blocks from other nodes
    other_chains = find_new_chains()
    # If our chain isn't longest,
    # then we store the longest chain
    longest_chain = blockchain
    for chain in other_chains:
        if len(longest_chain) < len(chain):
            longest_chain = chain
    # If the longest chain isn't ours,
    # then we stop mining and set
    # our chain to the longest one
    blockchain = longest_chain


def proof_of_work(last_proof):
    # Create a variable that we will use to find
    # our next proof of work
    incrementor = last_proof + 1
    # Keep incrementing the incrementor until
    # it's equal to a number divisible by 9
    # and the proof of work of the previous
    # block in the chain
    while not (incrementor % 9 == 0 and incrementor % last_proof == 0):
        incrementor += 1
    # Once that number is found,
    # we can return it as a proof
    # of our work
    return incrementor


@node.route('/mine', methods=['GET'])
def mine():
    # Get the last proof of work
    last_block = blockchain[len(blockchain) - 1]
    last_proof = last_block.data['proof-of-work']
    # Find the proof of work for
    # the current block being mined
    # Note: The program will hang here until a new
    #       proof of work is found
    proof = proof_of_work(last_proof)
    # Once we find a valid proof of work,
    # we know we can mine a block so
    # we reward the miner by adding a transaction
    #this_nodes_transactions.append(
    #    {"from": "network", "to": miner_address, "amount": 1}
    #)
    # Now we can gather the data needed
    # to create the new block
    new_block_data = {
        "proof-of-work": proof,
        "transactions": list(this_nodes_transactions)
    }
    new_block_index = last_block.index + 1
    new_block_timestamp = this_timestamp = date.datetime.now()
    last_block_hash = last_block.hash
    # Empty transaction list
    this_nodes_transactions[:] = []
    # Now create the
    # new block!
    mined_block = Block(
        new_block_index,
        new_block_timestamp,
        new_block_data,
        last_block_hash
    )
    blockchain.append(mined_block)
    # Let the client know we mined a block
    return json.dumps({
        "index": new_block_index,
        "timestamp": str(new_block_timestamp),
        "data": new_block_data,
        "hash": last_block_hash
    }) + "\n"


def checkAlreadyVoted(hash):

    for tx in this_nodes_transactions:
        if tx['from'][:90] == hash[:90]:
            return True

    for l in cache_alreadyvoted:
        if l == hash[:90]:
            return True

    for block in blockchain:
        if block.data["transactions"] != None:
            for tx in block.data["transactions"]:
                if tx['from'][:90] == hash[:90]:
                    return True

    return False


node.run()
