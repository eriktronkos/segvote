from subprocess import check_output
import requests
import json

candidato = input('Em qual candidato quer votar? ')
keys = raw_input('Qual o arquivo de chave? ')

sigvotacao = check_output(['./urs', '-sign-text', 'votacao', '-keyring', 'pubkeyring.keys', '-keypair', keys])

sigcand = check_output(['./urs', '-sign-text', 'cand'+str(candidato), '-keyring', 'pubkeyring.keys',  '-keypair', keys])

print requests.post('http://localhost:5000/txion', data=json.dumps({'from':sigvotacao, 'to':sigcand, 'id':candidato}), headers={'content-type': 'application/json'})