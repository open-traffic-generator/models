import snappi
api = snappi.api(host="10.22.40.53", version="8.50.0.465")
confObj = api.config()
port_1 = config.ports.port(name="p1", location='10.22.40.53/1/1')[-1]
port_2 = config.ports.port(name="p2", location='10.22.40.53/1/2')[-1]


device = confObj.devices.device(name="client").device(name="server")

device[0].port_name = port_1.name
device[1].port_name = port_2.name
#Client Configuration
eth1 = device[0].ethernets.ethernet()[-1]
eth1.mac = "00:00:00:00:65:01"
eth1.name = "eth_r1"
eth1.mtu = 1500

ipv4_1 = eth1.ipv4_addresses.iv4()[-1]
ipv4_1.name = "ipv4_1"
ipv4_1.address = "10.1.1.1"
ipv4_1.prefix = 24
ipv4_1.gateway = "10.1.1.2"

app1 = config.app.app()
app1.interface = ipv4_1.name 
tcp_1 = app1.tcp()
tcp_1.keep_alive_time = 700
tcp_1.receive_buffer_size = 4096
tcp_1.transmit_buffer_size = 4096
tcp_1.fin_timeout = 60
tcp_1.syn_retries = 5 
tcp_1.source_port_range.min = 1024
tcp_1.source_port_range.max = 65535


http_client = tcp_1.http.http()
http_client[0].role = "Client"
http_client[0].name = "HTTP Client1"
http_client[0].enable_ssl = "True"

#server configurations
eth3 = device[1].ethernets.ethernet()[-1]
eth3.mac = "00:00:00:00:70:01"
eth3.name = "eth_S1"
eth3.mtu = 1500

ipv4_3 = eth3.ipv4_addresses.ipv4()[-1]
ipv4_3.name = "ipv4_3"
ipv4_3.address = "10.1.1.2"
ipv4_3.prefix = 24
ipv4_3.gateway = "10.1.1.1"

app2 = config.app.app()
app2.interface = ipv4_3.name 
tcp_3 = app2.tcp()

tcp_3.keep_alive_time = 700
tcp_3.receive_buffer_size = 4096
tcp_3.transmit_buffer_size = 4096
tcp_3.fin_timeout = 60
tcp_3.syn_retries = 5 
tcp_3.source_port_range.min = 1024
tcp_3.source_port_range.max = 65535

http_server = tcp_3.http().http()
http_server[0].role = "Server"
http_server[0].name = "HTTP Server"
http_server[0].enable_ssl = "True"
http_server[0].page(name="customget", response=200, url="/b.html")

#Flow Configurations
f1 = confObj.flows.flow()
f1.tx_rx.tx(name=http_client[0].name)
f1.tx_rx.rx(name=http_server[0].name)

p1 = f1.trasaction().http.get(url="/b.html").post("/b.html")

#Objective and Traffic configurations
f1.test_type = "Simulated Users"
f1.test_value = 100
f1.duration.ramp_up = 10
f1.duration.sustain_time = 180
f1.duration.ramp_down = 180
api.set_config(confObj)
api.control(state= start)

