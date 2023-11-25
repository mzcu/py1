import telnetlib
import re
import prometheus_client as prom


# Prometheus exporter config
metrics_server_port = 8742
prefix = "p1"
default_labels = ["device", "version"]

# P1 reader config
p1_host = "192.168.2.185"
p1_port = 23


# Look for "P1 Companion Standard, Dutch Smart Meter Requirements" for more info
obis_to_prom = {
    "0-2:24.2.1": (
        prom.Counter(
            f"{prefix}_gas_m3",
            "gas volume delivered",
            default_labels,
        ),
        lambda v: float(v[v.index(")(") + 2 : v.index("*")]),
    ),
    "1-0:1.8.1": (
        prom.Counter(
            f"{prefix}_electricity_delivered_to_client_tariff_1_kwh",
            "meter reading electricity delivered to client (tariff 1 / daltarief)",
            default_labels,
        ),
        lambda v: float(v[0 : v.index("*")]),
    ),
    "1-0:1.8.2": (
        prom.Counter(
            f"{prefix}_electricity_delivered_to_client_tariff_2_kwh",
            "meter reading electricity delivered to client (tariff 2 / normaaltarief)",
            default_labels,
        ),
        lambda v: float(v[0 : v.index("*")]),
    ),
    "1-0:21.7.0": (
        prom.Gauge(
            f"{prefix}_active_power_delivered_l1_kw",
            "instantaneous active power l1 (+p) in w resolution",
            default_labels,
        ),
        lambda v: float(v[0 : v.index("*")]),
    ),
    "1-0:32.7.0": (
        prom.Gauge(
            f"{prefix}_voltage_l1_v",
            "instantaneous voltage l1 in v resolution",
            default_labels,
        ),
        lambda v: float(v[0 : v.index("*")]),
    ),
}


def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def publish(device_id, dsmr_version, records):
    for id, value in records:
        if id in obis_to_prom:
            metric, value_transformation = obis_to_prom[id]
            metric.labels(device=device_id, version=dsmr_version)._value.set(
                value_transformation(value)
            )


if __name__ == "__main__":
    prom.REGISTRY.unregister(prom.GC_COLLECTOR)
    prom.REGISTRY.unregister(prom.PLATFORM_COLLECTOR)
    prom.REGISTRY.unregister(prom.PROCESS_COLLECTOR)
    prom.start_http_server(metrics_server_port)
    equipment_identifier_obis = "0-0:96.1.1"
    dsmr_version_obis = "1-3:0.2.8"
    with telnetlib.Telnet(p1_host, p1_port) as tn:
        header, counters, crc, data = None, [], None, bytes()
        while True:
            readout = tn.read_until(b"!", timeout=2)
            crc = tn.read_until(b"\r\n", timeout=2)
            if not readout or not crc:
                exit(1)
            crc = int(crc[0:4].decode("utf-8"), 16)
            computed_crc = crc16(readout)
            if not crc == computed_crc:
                print(f"CRC mismatch for {readout}")
                continue
            header, data = readout.decode("utf-8").split("\r\n\r\n")
            records = []
            device_id = None
            dsmr_version = None
            for record in data.splitlines():
                if record != "!":
                    match = re.match(r"([0-9\:\-\.]+)\((.+)\)", record)
                    if match:
                        id, value = match.groups()
                        if id == equipment_identifier_obis:
                            device_id = value
                        elif id == dsmr_version_obis:
                            dsmr_version = value
                        records.append((id, value))
            publish(device_id, dsmr_version, records)
