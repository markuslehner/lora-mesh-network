# CURRENT SETUP
atm using global environment

## WEBSERVER
path to service folder
```
cd /lib/systemd/system/
```
configured service on raspberrypi: lora_webserver.service --> running web_server.py  
configured service on raspberrypi: lora_server.service --> running central_node_gps.py  

permissions are now with root user @pi --> not best practice  
ToDO figure out why service permissions are not high enough to access `/usr/local/lib/python3.10/site-packages/`  

what it does:  
- displays all packets in the database
- refreshing adds newly received packets


**Commands:**

after changing files:
```
sudo systemctl daemon-reload
sudo systemctl enable lora_webserver.service
```

check status:
```
sudo systemctl status lora_webserver.service
```

stop/start service
```
sudo systemctl start lora_webserver.service
sudo systemctl stop lora_webserver.service
```


show log:
```
sudo journalctl -f -u lora_webserver.service
```

## RECEIVER
To receive packets --> run the script `central_node.py`  
All captured packets are stored to the database
