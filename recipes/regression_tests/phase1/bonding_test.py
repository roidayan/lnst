import logging
from lnst.Controller.Task import ctl
from lnst.Controller.PerfRepoUtils import netperf_baseline_template
from lnst.Controller.PerfRepoUtils import netperf_result_template

# ------
# SETUP
# ------

mapping_file = ctl.get_alias("mapping_file")
perf_api = ctl.connect_PerfRepo(mapping_file)

product_name = ctl.get_alias("product_name")

m1 = ctl.get_host("testmachine1")
m2 = ctl.get_host("testmachine2")

m1.sync_resources(modules=["IcmpPing", "Icmp6Ping", "Netperf"])
m2.sync_resources(modules=["IcmpPing", "Icmp6Ping", "Netperf"])


# ------
# TESTS
# ------

offloads = ["tso", "gro", "gso"]

ipv = ctl.get_alias("ipv")
mtu = ctl.get_alias("mtu")
netperf_duration = int(ctl.get_alias("netperf_duration"))
nperf_reserve = int(ctl.get_alias("nperf_reserve"))
nperf_confidence = ctl.get_alias("nperf_confidence")
nperf_max_runs = int(ctl.get_alias("nperf_max_runs"))

test_if1 = m1.get_interface("test_if")
test_if1.set_mtu(mtu)
test_if2 = m2.get_interface("test_if")
test_if2.set_mtu(mtu)

ping_mod = ctl.get_module("IcmpPing",
                           options={
                               "addr" : m2.get_ip("test_if", 0),
                               "count" : 100,
                               "iface" : m1.get_devname("test_if"),
                               "interval" : 0.1
                           })

ping_mod6 = ctl.get_module("Icmp6Ping",
                           options={
                               "addr" : m2.get_ip("test_if", 1),
                               "count" : 100,
                               "iface" : m1.get_devname("test_if"),
                               "interval" : 0.1
                           })

netperf_srv = ctl.get_module("Netperf",
                              options = {
                                  "role" : "server",
                                  "bind" : m1.get_ip("test_if", 0)
                              })

netperf_srv6 = ctl.get_module("Netperf",
                              options={
                                  "role" : "server",
                                  "bind" : m1.get_ip("test_if", 1),
                                  "netperf_opts" : " -6",
                              })

netperf_cli_tcp = ctl.get_module("Netperf",
                                  options = {
                                      "role" : "client",
                                      "netperf_server" : m1.get_ip("test_if", 0),
                                      "duration" : netperf_duration,
                                      "testname" : "TCP_STREAM",
                                      "confidence" : nperf_confidence,
                                      "netperf_opts" : "-i %s -L %s" % (nperf_max_runs, m2.get_ip("test_if", 0))
                                })

netperf_cli_udp = ctl.get_module("Netperf",
                                  options = {
                                      "role" : "client",
                                      "netperf_server" : m1.get_ip("test_if", 0),
                                      "duration" : netperf_duration,
                                      "testname" : "UDP_STREAM",
                                      "confidence" : nperf_confidence,
                                      "netperf_opts" : "-i %s -L %s" % (nperf_max_runs, m2.get_ip("test_if", 0))
                                  })

netperf_cli_tcp6 = ctl.get_module("Netperf",
                                  options={
                                      "role" : "client",
                                      "netperf_server" :
                                          m1.get_ip("test_if", 1),
                                      "duration" : netperf_duration,
                                      "testname" : "TCP_STREAM",
                                      "confidence" : nperf_confidence,
                                      "netperf_opts" :
                                          "-i %s -L %s -6" % (nperf_max_runs, m2.get_ip("test_if", 1))
                                  })
netperf_cli_udp6 = ctl.get_module("Netperf",
                                  options={
                                      "role" : "client",
                                      "netperf_server" :
                                          m1.get_ip("test_if", 1),
                                      "duration" : netperf_duration,
                                      "testname" : "UDP_STREAM",
                                      "confidence" : nperf_confidence,
                                      "netperf_opts" :
                                          "-i %s -L %s -6" % (nperf_max_runs, m2.get_ip("test_if", 1))
                                  })

ctl.wait(15)

for offload in offloads:
    for state in ["off", "on"]:
        m1.run("ethtool -K %s %s %s" % (m1.get_devname("test_if"), offload,
                                        state))
        m2.run("ethtool -K %s %s %s" % (m2.get_devname("test_if"), offload,
                                        state))
        if ipv in [ 'ipv4', 'both' ]:
            m1.run(ping_mod)

            server_proc = m1.run(netperf_srv, bg=True)
            ctl.wait(2)

            # prepare PerfRepo result for tcp
            result_tcp = perf_api.new_result("tcp_ipv4_id",
                                             "tcp_ipv4_result",
                                             hash_ignore=[
                                                 'kernel_release',
                                                 'redhat_release'])
            result_tcp.set_parameter(offload, state)
            result_tcp.add_tag(product_name)

            baseline = perf_api.get_baseline_of_result(result_tcp)
            netperf_baseline_template(netperf_cli_tcp, baseline)

            tcp_res_data = m2.run(netperf_cli_tcp,
                                  timeout = (netperf_duration + nperf_reserve)*nperf_max_runs)

            netperf_result_template(result_tcp, tcp_res_data)
            perf_api.save_result(result_tcp)

            # prepare PerfRepo result for udp
            result_udp = perf_api.new_result("udp_ipv4_id",
                                             "udp_ipv4_result",
                                             hash_ignore=[
                                                 'kernel_release',
                                                 'redhat_release'])
            result_udp.set_parameter(offload, state)
            result_udp.add_tag(product_name)

            baseline = perf_api.get_baseline_of_result(result_udp)
            netperf_baseline_template(netperf_cli_udp, baseline)

            udp_res_data = m2.run(netperf_cli_udp,
                                  timeout = (netperf_duration + nperf_reserve)*nperf_max_runs)

            netperf_result_template(result_udp, udp_res_data)
            perf_api.save_result(result_udp)

            server_proc.intr()

        if ipv in [ 'ipv6', 'both' ]:
            m1.run(ping_mod6)

            server_proc = m1.run(netperf_srv6, bg=True)
            ctl.wait(2)

            # prepare PerfRepo result for tcp ipv6
            result_tcp = perf_api.new_result("tcp_ipv6_id",
                                             "tcp_ipv6_result",
                                             hash_ignore=[
                                                 'kernel_release',
                                                 'redhat_release'])
            result_tcp.set_parameter(offload, state)
            result_tcp.add_tag(product_name)

            baseline = perf_api.get_baseline_of_result(result_tcp)
            netperf_baseline_template(netperf_cli_tcp6, baseline)

            tcp_res_data = m2.run(netperf_cli_tcp6,
                                  timeout = (netperf_duration + nperf_reserve)*nperf_max_runs)

            netperf_result_template(result_tcp, tcp_res_data)
            perf_api.save_result(result_tcp)

            # prepare PerfRepo result for udp ipv6
            result_udp = perf_api.new_result("udp_ipv6_id",
                                             "udp_ipv6_result",
                                             hash_ignore=[
                                                 'kernel_release',
                                                 'redhat_release'])
            result_udp.set_parameter(offload, state)
            result_udp.add_tag(product_name)

            baseline = perf_api.get_baseline_of_result(result_udp)
            netperf_baseline_template(netperf_cli_udp6, baseline)

            udp_res_data = m2.run(netperf_cli_udp6,
                                  timeout = (netperf_duration + nperf_reserve)*nperf_max_runs)

            netperf_result_template(result_udp, udp_res_data)
            perf_api.save_result(result_udp)

            server_proc.intr()
