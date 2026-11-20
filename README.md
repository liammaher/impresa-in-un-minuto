# Impresa in un minuto

Controlla la cartella di un lavoro per una pratica del SUE e SUAP del Comune di Napoli, su impresainungiorno: ti dice
quale pratica serve, cosa leggono i documenti del tuo cliente (o della tua impresa), quali file lo
sportello rifiuterebbe e quali dati mancano. **In ChatGPT, per ora, non compila il portale**: non
apre impresainungiorno, non prepara bozze, non dichiara, non firma, non paga e non invia. Gratuito
e open source.

> **Per chi queste pratiche le presenta già.** Impresa in un minuto controlla: non è una consulenza e
> non decide al posto tuo. ChatGPT può sbagliare, e il controllo finale è tuo. Se non sai riconoscere
> un errore in una pratica, non usarlo.

## Cosa copre, e cosa no

- **Per ora il SUE e SUAP del Comune di Napoli**, su impresainungiorno; altri sportelli e comuni si aggiungono
  nel tempo.
  Per il SUAP: aprire, trasferire, ampliare, subentrare, sospendere o chiudere un negozio, un bar o
  ristorante, un acconciatore o un'estetista, per l'impresa che presenta con il proprio SPID. Un
  caso fuori da questi (alcolici, un edificio tutelato, un centro commerciale, un'impresa con altri
  soci) ChatGPT lo rifiuta subito, con il motivo. Gli allegati del SUAP vanno firmati digitalmente:
  li alleghi tu, ChatGPT non ne carica nessuno.
  Un immobile in un altro comune, un altro ente (Genio Civile, Soprintendenza, ASL, Catasto, Agenzia
  delle Entrate, Regione) o una pratica che Impresa in un minuto non conosce: ChatGPT ti dice subito che non è
  coperta dall'automazione, e non apre nulla.
- Per ogni lavoro ChatGPT ti dice se la pratica è **coperta** (Impresa in un minuto ne conosce ogni
  passo sul portale), se ha **solo indicazioni** o se **non è coperta**, e perché.

- Le regole vengono dalla biblioteca delle procedure, ogni fatto con la sua fonte. Ciò che la
  biblioteca non copre, ChatGPT lo dice.

## Installazione

Serve l'app ChatGPT per computer (Mac o Windows): Impresa in un minuto compila nel suo browser, e
non funziona in ChatGPT sul web o sul telefono.

1. In Codex, nell'app, aggiungi il marketplace `liammaher/impresa-in-un-minuto` e installa il plugin
   **Impresa in un minuto**. Se usi Codex anche nel terminale, è lo stesso:
   `codex plugin marketplace add liammaher/impresa-in-un-minuto`, poi
   `codex plugin add impresa-in-un-minuto@impresa-in-un-minuto`.
2. Chiudi e riapri l'app: il plugin si carica all'avvio.
3. Per aggiornarlo (Impresa in un minuto cambia quando cambia il portale): aggiorna il marketplace
   (nel terminale `codex plugin marketplace upgrade`), poi chiudi e riapri l'app. Fallo ogni tanto e
   prima di una pratica importante.

Poi apri nell'app la cartella del lavoro (quella con i documenti del cliente) oppure la cartella
dei tuoi lavori, con una sottocartella per ogni lavoro. I dati dello studio li chiede ChatGPT alla
prima pratica; con la cartella dei lavori, una volta sola.
Serve Python 3 sul computer: su un Mac che non lo ha, alla prima pratica macOS propone di
installare gli strumenti per sviluppatori di Apple, che lo contengono; accetta. Su Windows
installalo da python.org.

## Come si usa

1. Metti i documenti di ogni lavoro in una cartella, una per lavoro: visura, atto o contratto,
   documento d'identità, relazione tecnica, elaborati. Apri in Codex, nell'app, quella cartella (o la
   cartella che contiene tutti i lavori). I documenti non si toccano: ChatGPT non li sposta e non li
   rinomina; i suoi file di lavoro stanno in una sola sottocartella, «impresa-in-un-minuto», che puoi
   cancellare a lavoro finito.
2. Scrivi una riga: «solo un controllo: CILA per il signor Bianchi, i documenti sono nella cartella
   Bianchi».
3. ChatGPT risponde con un solo messaggio: quale pratica serve, cosa ha capito dai documenti, quali
   file lo sportello rifiuterebbe e perché, e quanti dati mancano. Il portale lo compili tu.

## Dove vanno i dati dei tuoi clienti

Nella cartella dei tuoi lavori su questo computer e nella conversazione con ChatGPT: sul portale no,
perché in ChatGPT Impresa in un minuto non lo apre. Impresa in un minuto non ha un server suo. I dati
che ChatGPT legge dai documenti restano in chiaro nella sottocartella «impresa-in-un-minuto» della
cartella del lavoro: se la cartella è sincronizzata (Dropbox, OneDrive, Drive), lo sono anche loro.
Cancellala a lavoro finito. **ChatGPT legge i documenti del lavoro**: i dati dei clienti (nomi,
codici fiscali, indirizzi, dati catastali) passano quindi dalla conversazione con ChatGPT, come ogni
documento che tu vi apri. Se un cliente non vuole che i suoi documenti passino da ChatGPT, non usare
Impresa in un minuto per quel lavoro.

Password, PIN e accesso SPID mai: l'accesso al portale lo fai tu.
Sei titolare del trattamento dei dati dei tuoi clienti.
Nelle impostazioni di ChatGPT disattiva «Migliora il modello per tutti» e usa il browser
dell'app, non il tuo Chrome.

## Prima di usarlo

Impresa in un minuto **non è uno strumento ufficiale**: non è affiliato al Comune di Napoli, a
InfoCamere (che gestisce impresainungiorno) né ad altri enti, e non è una consulenza legale. Il nome
gioca con quello del portale, ma è un progetto indipendente, gratuito e open source.

Leggi l'[uso responsabile](https://github.com/liammaher/impresa-in-un-minuto/blob/main/docs/responsible-use.md).
In breve: tu firmi e rispondi della pratica; una pratica alla volta, con il tuo SPID; nessun dato
personale in una segnalazione. Per chiedere una pratica o segnalare un portale cambiato apri una
[segnalazione](https://github.com/liammaher/impresa-in-un-minuto/issues/new/choose).
Se qualcosa di Impresa in un minuto non funziona, dillo a ChatGPT: ti prepara la segnalazione già
compilata, senza i dati dei clienti, e tu la rileggi prima di inviarla.

## Per qualcosa in più

Per collegarlo agli altri strumenti dello studio, usarlo su molti lavori insieme o automatizzare
altro, scrivi a liampmaher1996@gmail.com.
