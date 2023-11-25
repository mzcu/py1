# Minimal Prometheus exporter for P1-E20

Telnets to P1-E20 ethernet reader and exposes received data as Prometheus metrics.

## Installation

```shell
python -m venv .env`
source .env/bin/activate
pip install -r requirements.txt
```


## Usage

Point to your P1-E20 by modifying host and port variables on top of `py1.py` file and run with `python py1.py`. By default, it exposes Prometheus metrics on `http://localhost:8742/metrics`.

## Other

I guess you'd want to install a unit file and let systemd keep this process running for you.
