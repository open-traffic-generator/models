array of dhcp clients over a eth not a valid usecase. OC model has only reference to dhcpclient

  // Case-1: DHCP Client & Server are Keysight and Relay Agent as DUT.
  //   DHCPV4-Client(x.x.x.x)<-------> (1.1.1.1)RelayAgent(DUT)(2.2.2.1) <------>(2.2.2.2) DHCPV4-Server
  // DHCP Client is configured on connected interface.
  
  config := gosnappi.NewConfig()

	// add ports
	p1 := config.Ports().Add().SetName("p1").SetLocation(opts.IxiaCPorts()[0])
	p2 := config.Ports().Add().SetName("p2").SetLocation(opts.IxiaCPorts()[1])

	// add devices
	d1 := config.Devices().Add().SetName("p1d1")
	d2 := config.Devices().Add().SetName("p2d1")s

	// add protocol stacks for device d1
	d1Eth1 := d1.Ethernets().
		Add().
		SetName("p1d1eth").
		SetMac("00:00:01:01:01:01").
		SetMtu(1500)

	d1Eth1.Connection().SetPortName(p1.Name())

	p1d1DhcpV4Client := d1Eth1.
		DhcpClient().
		V4().
		SetName("p1d1dhcpv4").
    SetChoice(gosnappi.conn_eth_name.CONN_ETH=d1Eth1.Name())
		

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
		SetRxNames([]string{p2d2DhcpV4Server.Name()})

	f1Eth := f1.Packet().Add().Ethernet()
	f1Eth.Src().SetValue(d1Eth1.Mac())
	f1Eth.Dst().Auto()

	f1Ip := f1.Packet().Add().Ipv4()
	f1Ip.Src().SetValue("10.10.10.1")
	f1Ip.Dst().SetValue("20.20.20.1")

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
	f2Ip.Src().SetValue("20.20.20.1")
	f2Ip.Dst().SetValue("10.10.10.1")


// Case-2: DHCP Client Behind the  Relay Agent and are Keysight and DHCP Server as Keysight/DUT.
//   DHCPV4-Client(x.x.x.x)<------->RelayAgent(DUT)(2.2.2.1) <------>(2.2.2.2) DHCPV4-Server
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
  d1Eth2 := d1.Ethernets().
		Add().
		SetName("p1d1eth2").
		SetMac("00:00:01:01:01:01").
	d1Eth1.Connection().SetPortName(d1Eth1.Name())

// Configure a IPv4 stack
  d1p1Ipv4 := d1Eth1.
		Ipv4Addresses().
		Add().
		SetName("p1d1ipv4").
		SetAddress("1.1.1.2").
		SetGateway("1.1.1.1").
		SetPrefix(32)

  // Configure a (place holder) Relay Agent
	d1p1RelayAgent := d2.RelayAgent().Dhcpv4().
		SetName("d1p1RelayAgent1").
    SetIpv4Name(d1p1Ipv4.Name())

	p1d1DhcpV4Client := d1Eth1.
		DhcpClient().
		V4().
		SetName("p1d1dhcpv4").
    SetChoice(gosnappi.conn_eth_name.RELAY_AGENT_NAME=d1p1RelayAgent.Name())
		

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
		SetRxNames([]string{p2d2DhcpV4Server.Name()})

	f1Eth := f1.Packet().Add().Ethernet()
	f1Eth.Src().SetValue(d1Eth1.Mac())
	f1Eth.Dst().Auto()

	f1Ip := f1.Packet().Add().Ipv4()
	f1Ip.Src().SetValue("10.10.10.1")
	f1Ip.Dst().SetValue("20.20.20.1")

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
	f2Ip.Src().SetValue("20.20.20.1")
	f2Ip.Dst().SetValue("10.10.10.1")

  //Case-3: BGP over DHCP Client on Port 1 & DHCP Server on Port2.
  config := gosnappi.NewConfig()

	// add ports
	p1 := config.Ports().Add().SetName("p1").SetLocation(opts.IxiaCPorts()[0])
	p2 := config.Ports().Add().SetName("p2").SetLocation(opts.IxiaCPorts()[1])

	// add devices
	d1 := config.Devices().Add().SetName("p1d1")
	d2 := config.Devices().Add().SetName("p2d1")s

	// add protocol stacks for device d1
	d1Eth1 := d1.Ethernets().
		Add().
		SetName("p1d1eth").
		SetMac("00:00:01:01:01:01").
		SetMtu(1500)

	d1Eth1.Connection().SetPortName(p1.Name())

	p1d1DhcpV4Client := d1Eth1.
		DhcpClient().
		V4().
		SetName("p1d1dhcpv4").
    SetChoice(gosnappi.conn_eth_name.CONN_ETH=d1Eth1.Name())
		
	d1Bgp := d1.Bgp().
		SetRouterId("1.1.1.2")

	// Link DHCP Client name
	d1BgpIpv4Interface1 := d1Bgp.
		Ipv4Interfaces().Add().
		SetIpv4Name(p1d1DhcpV4Client.Name())

	d1BgpIpv4Interface1Peer1 := d1BgpIpv4Interface1.
		Peers().
		Add().
		SetAsNumber(2222).
		SetAsType(gosnappi.BgpV4PeerAsType.EBGP).
		SetPeerAddress("1.1.1.1").
		SetName("p1d1bgpv4")

	d1BgpIpv4Interface1Peer1V4Route1 := d1BgpIpv4Interface1Peer1.
		V4Routes().
		Add().
		SetNextHopIpv4Address("1.1.1.2").
		SetName("p1d1peer1rrv4").
		SetNextHopAddressType(gosnappi.BgpV4RouteRangeNextHopAddressType.IPV4).
		SetNextHopMode(gosnappi.BgpV4RouteRangeNextHopMode.MANUAL)

	d1BgpIpv4Interface1Peer1V4Route1.Addresses().Add().
		SetAddress("10.10.10.1").
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
    SetStartPoolAddress("100.1.1.1").
    SetPrefix(24).
    SetStep(1)
