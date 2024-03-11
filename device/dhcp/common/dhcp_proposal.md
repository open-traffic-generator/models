1. Array of dhcp clients over a eth not a valid usecase. OC model has only reference to dhcpclient [previous comment taken care]
2. dhcp_v4interface
	 dhcp_v6interface
	 two separate interfaces , no choice. [Incorporated]
3. DHCP relay-agent 4/6 are array. [Incorporated]

4. dhcpv4/v6 -> eth_name not required [Incorporated]

5. How to uniquely map to a relay agent [Yet to be done] 
5.1: why Client side IP is required in relay agent.
[From a capture from IxNetwork, its seen that DHCP discovery packet forwared to server
 a) IP src: client-side-ip b)IP-dst: IP of DHCP server's IP stack, and DHCP payload c) relay-agent-ip: client-side-ip
 From DHCP offer packet from:
 a) IP-dst: IP of DHCP server's IP stack, b) IP dst: IP P of Relay agent's IP stack]

6. Traffic auto filling up f1Ip.Src().AutoDhcp() [Incorporated]
8. Another alternative model to be created with unconnected ethernet without other exposed paramters rather mac and dhcp interfaces. [Yet to be done]
7. Just to note for partial start for dhcp/server for bgp start later after dhcp comes up first.
	
  // Case-1: DHCP Client & Server are Keysight and Relay Agent as DUT.
  //   DHCPV4-Client(x.x.x.x)<-------> (1.1.1.1)RelayAgent(DUT)(2.2.2.1) <------>(2.2.2.2) DHCPV4-Server(Pool: 100.1.1.1)
  // DHCP Client is configured on connected interface.
  
		config := gosnappi.NewConfig()
		// add ports
		p1 := config.Ports().Add().SetName("p1").SetLocation(opts.IxiaCPorts()[0])
		p2 := config.Ports().Add().SetName("p2").SetLocation(opts.IxiaCPorts()[1])

		// add devices
		d1 := config.Devices().Add().SetName("p1d1")
		d2 := config.Devices().Add().SetName("p2d1")

		// add protocol stacks for device d1
		d1Eth1 := d1.Ethernets().
			Add().
			SetName("p1d1eth").
			SetMac("00:00:01:01:01:01").
			SetMtu(1500)
		d1Eth1.Connection().SetPortName(p1.Name())

		p1d1DhcpV4Client := d1Eth1.
			DhcpV4interface().
			SetName("p1d1dhcpv4").
			SetEthName(d1Eth1.Name())
		
		// add protocol stacks for device d2
		d2Eth1 := d2.Ethernets().
			Add().
			SetName("p2d1eth").
			SetMac("00:00:02:02:02:02").
			SetMtu(1500)
		d2Eth1.Connection().SetPortName(p2.Name())

		d2p2Ipv4 := d2Eth1.
			Ipv4Addresses().
			Add().
			SetName("p2d1ipv4").
			SetAddress("2.2.2.2").
			SetGateway("2.2.2.1").
			SetPrefix(32)

		d2p2DhcpServerv4Iface1 := d2.DhcpServer().V4Server().
			Ipv4Interfaces().Add().
			SetIpv4Name("p2d1ipv4") //

		p2d2DhcpV4Server := d2Dhcpv4Iface1.
			v4().
			SetName("p2d2DhcpV4Server")

		p2d2DhcpV4Server.SetLeaseTime(1000).
			SetPoolSize(100).
			SetStartPoolAddress("100.1.1.1").
			SetPrefix(24).
			SetStep(1)


		// add endpoints and packet description flow 1
		f1 := config.Flows().Items()[0]
		f1.SetName(p1.Name() + " -> " + p2.Name()).
			TxRx().Device().
			SetTxNames([]string{p1d1DhcpV4Client.Name()}).
			SetRxNames([]string{d2p2DhcpServerv4Iface1.Ipv4Name()})

		f1Eth := f1.Packet().Add().Ethernet()
		f1Eth.Src().SetValue(d1Eth1.Mac())
		f1Eth.Dst().Auto()

		f1Ip := f1.Packet().Add().Ipv4()
		f1Ip.Src().AutoDhcp()
		f1Ip.Dst().SetValue("2.2.2.2")

		// add endpoints and packet description flow 2
		f2 := config.Flows().Items()[1]
		f2.SetName(p2.Name() + " -> " + p1.Name()).
			TxRx().Device().
			SetTxNames([]string{p2d2DhcpV4Server.Name()}).
			SetRxNames([]string{p1d1DhcpV4Client.ConnEthName()})

		f2Eth := f2.Packet().Add().Ethernet()
		f2Eth.Src().SetValue(d2Eth1.Mac())
		f2Eth.Dst().Auto()

		f2Ip := f2.Packet().Add().Ipv4()
		f2Ip.Src().SetValue("2.2.2.2")
		f2Ip.Dst().AutoDhcp()

// Case-2: DHCP Client Behind the  Relay Agent and are Keysight and DHCP Server as Keysight/DUT.
// DHCPV4-Client(x.x.x.x)<------->(100.1.1.1)RelayAgent(DUT)(2.2.2.1) <------>(2.2.2.2) DHCPV4-Server(Pool: 100.1.1.1)
// DHCP Client is configured on unconnected connected interface.

		config := gosnappi.NewConfig()

		// add ports
		p1 := config.Ports().Add().SetName("p1").SetLocation(opts.IxiaCPorts()[0])
		p2 := config.Ports().Add().SetName("p2").SetLocation(opts.IxiaCPorts()[1])

		// add devices
		d1 := config.Devices().Add().SetName("p1d1")
		d2 := config.Devices().Add().SetName("p2d1")

		// add protocol stacks for device d1 where Relay Agent will be configureds
		d1Eth1 := d1.Ethernets().
			Add().
			SetName("p1d1eth").
			SetMac("00:00:01:01:01:01").
			SetMtu(1500)
		d1Eth1.Connection().SetPortName(p1.Name())

		// Chained Ethernet where DHCPClient behind the Relay Agent will be configured.
		d1ChainedEth2 := d1.Ethernets().
			Add().
			SetName("p1d1eth2_chained").
			SetMac("00:00:01:01:01:01").
		d1Eth1.Connection().SetPortName(d1Eth1.Name())

	// Configure a IPv4 stack
		d1p1Ipv4 := d1Eth1.
			Ipv4Addresses().
			Add().
			SetName("p1d1ipv4").
			SetAddress("2.2.2.1").
			SetGateway("2.2.2.2").
			SetPrefix(24)

		// Configure a (place holder) Relay Agent
		
		d1BgpIpv4Interface1 := d1Bgp.
			Ipv4Interfaces().Add().
			SetIpv4Name(p1d1DhcpV4Client.Name())

		d1BgpIpv4Interface1Peer1 := d1BgpIpv4Interface1.
			Peers().
			Add().
			SetAsNumber(2222).
			SetAsType(gosnappi.BgpV4PeerAsType.EBGP).
			SetPeerAddress("22.22.22.1").
			SetName("p1d1bgpv4")

		d1p1RelayAgent := d2.RelayAgent()
		  IpV4interfaces().Add().V4RAInst().
			SetName("d1p1RelayAgent1").
			SetIpv4Name(d1p1Ipv4.Name()).
			SetCliendSideAddress("100.1.1.1")
			SetDhcpServer("2.2.2.2")

		p1d1DhcpV4Client := d1Eth2.
			dhcp_v4interface().
			SetName("p1d1dhcpv4").
			SetEthName(d1ChainedEth2.Name())
		
		// add protocol stacks for device d2
		d2Eth1 := d2.Ethernets().
			Add().
			SetName("p2d1eth").
			SetMac("00:00:02:02:02:02").
			SetMtu(1500)

		d2Eth1.Connection().SetPortName(p2.Name())

		d2p2Ipv4 := d2Eth1.
			Ipv4Addresses().
			Add().
			SetName("p2d1ipv4").
			SetAddress("2.2.2.2").
			SetGateway("2.2.2.1").
			SetPrefix(24)

		d2p2DhcpServerv4Iface1 := d2.DhcpServer().V4Server().
			Ipv4Interfaces().Add().
			SetIpv4Name("p2d1ipv4") //

		p2d2DhcpV4Server := d2Dhcpv4Iface1.
			v4().
			SetName("p2d2DhcpV4Server")

		p2d2DhcpV4Server.SetLeaseTime(1000).
			SetPoolSize(100).
			SetStartPoolAddress("100.1.1.2").
			SetPrefix(24).
			SetStep(1)

		// add endpoints and packet description flow 1
		f1 := config.Flows().Items()[0]
		f1.SetName(p1.Name() + " -> " + p2.Name()).
			TxRx().Device().
			SetTxNames([]string{p1d1DhcpV4Client.Name()}).
			SetRxNames([]string{d2p2DhcpServerv4Iface1.Ipv4Name()})

		f1Eth := f1.Packet().Add().Ethernet()
		f1Eth.Src().SetValue(d1Eth1.Mac())
		f1Eth.Dst().Auto()

		f1Ip := f1.Packet().Add().Ipv4()
		f1Ip.Src().Auto()
		f1Ip.Dst().SetValue("2.2.2.2")

		// add endpoints and packet description flow 2
		f2 := config.Flows().Items()[1]
		f2.SetName(p2.Name() + " -> " + p1.Name()).
			TxRx().Device().
			SetTxNames([]string{p2d2DhcpV4Server.Name()}).
			SetRxNames([]string{p1d1DhcpV4Client.ConnEthName()})

		f2Eth := f2.Packet().Add().Ethernet()
		f2Eth.Src().SetValue(d2Eth1.Mac())
		f2Eth.Dst().Auto()

		f2Ip := f2.Packet().Add().Ipv4()
		f2Ip.Src().SetValue("2.2.2.2")
		f2Ip.Dst().Auto()

//Case-3: BGP over DHCP Client on Port 1 & DHCP Server and BGP peer (over loopback)on Port2.
  config := gosnappi.NewConfig()

		// add ports
		p1 := config.Ports().Add().SetName("p1").SetLocation(opts.IxiaCPorts()[0])
		p2 := config.Ports().Add().SetName("p2").SetLocation(opts.IxiaCPorts()[1])

		// add devices
		d1 := config.Devices().Add().SetName("p1d1")
		d2 := config.Devices().Add().SetName("p2d1")
		p2Chained1 := config.Devices().Add().SetName("p2_chained1")

		// add protocol stacks for device d1
		d1Eth1 := d1.Ethernets().
			Add().
			SetName("p1d1eth").
			SetMac("00:00:01:01:01:01").
			SetMtu(1500)

		d1Eth1.Connection().SetPortName(p1.Name())

		p1d1DhcpV4Client := d1Eth1.
			dhcp_v4interface().
			SetName("p1d1dhcpv4").
			SetEthName(d1Eth1.Name())
		
		d1Bgp := d1.Bgp().
			SetRouterId("1.1.1.2")

		// Link with DHCP Client name
		d1BgpIpv4Interface1 := d1Bgp.
			Ipv4Interfaces().Add().
			SetIpv4Name(p1d1DhcpV4Client.Name())

		d1BgpIpv4Interface1Peer1 := d1BgpIpv4Interface1.
			Peers().
			Add().
			SetAsNumber(2222).
			SetAsType(gosnappi.BgpV4PeerAsType.EBGP).
			SetPeerAddress("22.22.22.1").
			SetName("p1d1bgpv4")

		d1BgpIpv4Interface1Peer1V4Route1 := d1BgpIpv4Interface1Peer1.
			V4Routes().
			Add().
			SetNextHopIpv4Address("1.1.1.2").
			SetName("p1d1peer1rrv4").
			SetNextHopAddressType(gosnappi.BgpV4RouteRangeNextHopAddressType.IPV4).
			SetNextHopMode(gosnappi.BgpV4RouteRangeNextHopMode.MANUAL)

		d1BgpIpv4Interface1Peer1V4Route1.Addresses().Add().
			SetAddress("100.10.10.1").
			SetPrefix(32).
			SetCount(4).
			SetStep(1)

		d1BgpIpv4Interface1Peer1V4Route1.Advanced().
			SetMultiExitDiscriminator(50).
			SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)

			// add protocol stacks for device d2
		d2Eth1 := d2.Ethernets().
			Add().
			SetName("p2d1eth").
			SetMac("00:00:02:02:02:02").
			SetMtu(1500)

		d2Eth1.Connection().SetPortName(p2.Name())

		d2p2Ipv4 := d2Eth1.
			Ipv4Addresses().
			Add().
			SetName("p2d1ipv4").
			SetAddress("2.2.2.2").
			SetGateway("2.2.2.1").
			SetPrefix(32)

		d2p2DhcpServerv4Iface1 := d2.DhcpServer().V4Server().
			Ipv4Interfaces().Add().
			SetIpv4Name("p2d1ipv4") //

		p2d2DhcpV4Server := d2Dhcpv4Iface1.
			v4().
			SetName("p2d2DhcpV4Server")

		p2d2DhcpV4Server.SetLeaseTime(1000).
			SetPoolSize(100).
			SetStartPoolAddress("21.21.21.1").
			SetPrefix(24).
    	SetStep(1)

	// Port2 first chained device.
		p2Lo1 := p2Chained1.Ipv4Loopbacks().
			Add().
			SetName("p2chaineddev1.v4lo1").
			SetAddress("22.22.22.1").
			SetEthName(d1Eth1.Name())

		p2Lo1Bgp := p2Chained1.Bgp().
			SetRouterId(p2Lo1.Address())

		p2Lo1BgpIpv4Interface1 := p2Lo1Bgp.
			Ipv4Interfaces().Add().
			SetIpv4Name("p2chaineddev1.v4lo1")

		p2Lo1BgpIpv4Interface1Peer1 := p2Lo1BgpIpv4Interface1.
			Peers().
			Add().
			SetAsNumber(1111).
			SetAsType(gosnappi.BgpV4PeerAsType.IBGP).
			SetPeerAddress("21.21.21.1").
			SetName("p2lo1bgpv4")

		p2Lo1BgpIpv4Interface1Peer1V4Route1 := p2Lo1BgpIpv4Interface1Peer1.
			V4Routes().
			Add().
			SetName("p2lo1peer1rrv4")

		p2Lo1BgpRrAddr := p2Lo1BgpIpv4Interface1Peer1V4Route1.Addresses().Add().
			SetAddress("200.1.1.1").
			SetPrefix(32)

		p2Lo1BgpIpv4Interface1Peer1V4Route1.Advanced().
			SetMultiExitDiscriminator(50).
			SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)
