# Observer HTTP et HTTPS dans Wireshark

Cette demonstration envoie uniquement un message JSON fixe a deux serveurs
temporaires sur `127.0.0.1`. Elle ne lance aucune commande systeme et ne change
pas le programme de la Leonardo. Les serveurs s'arretent apres la capture.

## Comparer les deux captures

Les fichiers se trouvent dans `.local/http-https-demo/` :

- `http-https.pcapng` : capture originale, sans les cles TLS.
- `http-https-with-keys.pcapng` : meme capture avec les secrets TLS de cette demo
  incorpores, pour permettre a Wireshark de dechiffrer la session.
- `results.json` : reponses des deux tests.

Dans la capture originale :

1. Appliquer `tcp.port == 8080` pour voir HTTP. Selectionner le `POST /demo`,
   puis clic droit > Follow > TCP Stream : `SALUT_WIRESHARK` est lisible.
2. Appliquer `tcp.port == 8443` pour voir HTTPS. Le Client Hello, le Server Hello,
   les adresses, les tailles et les horaires sont visibles. Les donnees utiles
   apparaissent comme `Application Data` chiffrees.

Dans la capture avec cles :

1. Appliquer `tcp.port == 8443 && http`.
2. Selectionner le `POST /demo`, puis Follow > TLS Stream : le meme message JSON
   devient lisible grace aux cles fournies par notre client de test.

Si les protocoles ne sont pas reconnus automatiquement, utiliser Analyze >
Decode As : TCP 8080 vers HTTP, TCP 8443 vers TLS.

## Refaire la demo

Avec Python, le module `cryptography`, Wireshark et Npcap installes :

```powershell
python .\http_https_demo.py
```

Le script capture uniquement les ports 8080 et 8443 sur l'interface loopback.
Il genere un certificat local valable un jour ; seul son propre client lui fait
confiance, sans modifier les certificats de Windows ni desactiver la verification
TLS. Les fichiers de demonstration sont remplaces a chaque execution.

References : [capture loopback sous Windows](https://wiki.wireshark.org/CaptureSetup/Loopback),
[dechiffrement TLS dans Wireshark](https://wiki.wireshark.org/TLS/).
