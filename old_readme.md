## How it works:

you would start to set up the virtual environment in which helps to keep your python clean and prevent errors in the future. and to do so:
For Linux:

- install the following:

````
apt-get install python3-virtualenv virtualenv
````

- create a folder in wanted path

````
mkdir <folderName>
````

- then run the command:

````
virtualenv -p python3 jm-env
````

- finally, activate the environment:

````
source <folderName>/bin/activate
````

## Run the CMinor:

first of all, run the server side **cminor,py** to be ready to communicate with the client side.

````
python cminor.py
````

while the server is running, go and run the **cminor_client,py**. the client would have different arguments whether update, qurey, subscribe or unsubscribe.

**To do update we simply write:**

````
python cminor_client.py -u -p <YOUR_PAYLOAD>
````

**To do query:**

````
python cminor_client.py -q -p <YOUR_PAYLOAD>
````

**To do subscribe:**

````
python cminor_client.py -s -p <YOUR_PAYLOAD>
````

**To do unsubscribe:**

````
python cminor_client.py -uns -p <YOUR_PAYLOAD>
````

- -u : To submit an update.
- -q : To submit an quey.
- -s : To submit an subscribe.
- -uns : To submit an unsubscribe.
- -p : To submit an pylaod.
- <YOUR_PAYLOAD> : For payload if you would enter a sentens it should be within a quotation mark **' YOUR PAYLAOD '**.