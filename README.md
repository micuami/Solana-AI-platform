# Solana-AI-platform

## Frontend
- login cu user(adaugam si un cont de admin cu parola admin) -> 1
- pagina cu lista modele -> 2
- pagina cu lista baze de date -> 3
  
## Backend
- conectare cu baza de date pentru useri -> 1
- incarcarea modelelor intr-o baza de date -> 2 
- incarcarea bazelor de date in baze de date(boom) -> 3

- folosim flask pt server
- logica pentru contracte
  
## Blockchain <-> rust
- creare smart contract intre doua parti

cand un utilizator isi creaza cont pe platforma i se deschide un solana   account ??? (poate sa aiba account -> verifica daca exista contul)


pt flask:

from flask import Flask, request

app = Flask(__name__)

#pagina de baza a site-ului
@app.route('/')
def hello_world():
   return render_template("index.html")
   
if __name__ == '__main__':
    app.run(debug=True, port=5000)
