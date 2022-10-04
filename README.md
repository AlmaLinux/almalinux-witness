# almalinux-witness

The AlmaLinux OS Project monitoring tool.


## Deployment and initial configuration

This section describes a local development environment deployment and
configuration.


### Pre-requirements

Create docker volume mount directories:

```shell
$ mkdir -p volumes/influxdb/data
$ mkdir -p volumes/mosquitto/{data,log}
```

Initialize a virtual environment:

```shell
$ virtualenv --system-site-packages env
$ . env/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
```

Enable masquerading if you are going to access Witness outside your localhost:

```shell
$ firewall-cmd --zone=public --add-masquerade --permanent
$ firewall-cmd --reload
```

Create an empty `telegraf-vars.env` file in the project's root:

```shell
$ install -m 600 /dev/null telegraf-vars.env
```

Create an empty Grafana configuration file:

```shell
$ install -m 600 /dev/null volumes/grafana/grafana.ini
```


### InfluxDB database initialization

First, you need to initialize the InfluxDB database (don't forget to either
define corresponding environment variables or replace them with desired
values):

```shell
$ UGID="$(id -u):$(id -g)" docker-compose run \
    -e DOCKER_INFLUXDB_INIT_ORG=AlmaLinux \
    -e DOCKER_INFLUXDB_INIT_BUCKET=distro_spread \
    -e DOCKER_INFLUXDB_INIT_MODE=setup \
    -e DOCKER_INFLUXDB_INIT_USERNAME="${INFLUX_ADMIN_USER}" \
    -e DOCKER_INFLUXDB_INIT_PASSWORD="${INFLUX_ADMIN_PASSWORD}" \
    -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN="${INFLUX_ADMIN_TOKEN}" \
    influxdb
```

Save the provided `${INFLUX_ADMIN_USER}`, `${INFLUX_ADMIN_PASSWORD}` and
`${INFLUX_ADMIN_TOKEN}` values into a secure place because you will need them
for InfluxDB administration purposes.

Wait until you will see the following log messages on your console:

```
2021-06-09T21:10:26.686975Z     info    Listening       {"log_id": "0UdedM~W000", "service": "tcp-listener", "transport": "http", "addr": ":8086", "port": 8086}
2021-06-09T21:10:26.687147Z     info    Starting        {"log_id": "0UdedM~W000", "service": "telemetry", "interval": "8h"}
```

then terminate the docker-compose process with `Ctrl-c`.


### Telegraf token creation

When you have the InfluxDB database initialized, you need to create an
unprivileged token for [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/).

Run the `influxdb` container:

```shell
$ UGID="$(id -u):$(id -g)" docker-compose up influxdb
```

open another terminal to find an InfluxDB bucket ID and generate a token for it:

```console
$ export UGID="$(id -u):$(id -g)"

# get an InfluxDB bucket ID and save it to the `BUCKET_ID` environment variable 
$ BUCKET_ID=$(docker compose exec influxdb \
               influx bucket list -o AlmaLinux -t "${INFLUX_ADMIN_TOKEN}" \
               | grep -oP '^(\w+)(?=\s+distro_spread)')

# generate an InfluxDB authentication token
$ docker compose exec influxdb \
    influx auth create --org AlmaLinux --read-bucket "${BUCKET_ID}" \
                       --write-bucket "${BUCKET_ID}" -t "${INFLUX_ADMIN_TOKEN}"

ID			Description	Token												User Name	User ID			Permissions
0a14e74bbb95c000			XMmTAPjfIuWw4FafnT84qDyYLTE9JtANoQ1ycOPbxzNWbtAWwAJpLoZhYhoosPAzXrm_gDXtWuWtHyrm1wsxBw==	witnessadm	0a149498f697a000	[read:orgs/6d0c4906bee90d15/buckets/08e28f1c21460f02 write:orgs/6d0c4906bee90d15/buckets/08e28f1c21460f02]
```

the last command will print a generated token and some additional information.
Add this token to the `telegraf-vars.env` file in the project's root:

```shell
INFLUX_TOKEN='ENTER_TELEGRAF_TOKEN_HERE'
```

Now you can safely terminate the docker-compose process running the `influxdb`
container.


### Grafana configuration

Configure a Grafana administrator password:

```shell
$ echo 'ENTER_PASSWORD_HERE' > volumes/grafana/admin_password
$ chmod 600 volumes/grafana/admin_password
```

Create an InfluxDB datasource configuration file
`volumes/grafana/provisioning/datasources/datasource.yaml` with the following
content:

```yaml
apiVersion: 1

datasources:
  - name: Witness-InfluxDB-Flux
    type: influxdb
    url: http://influxdb:8086/
    access: proxy
    isDefault: true
    secureJsonData:
      token: 'ENTER_INFLUXDB_TOKEN_HERE'
    jsonData:
      version: Flux
      organization: AlmaLinux
      defaultBucket: distro_spread
      tlsSkipVerify: true
      timeInterval: "1m"
```


### Running the system

Execute the following command in order to launch InfluxDB, Mosquitto and
Telegraf:

```shell
$ UGID="$(id -u):$(id -g)" docker-compose up
```

Use the `admin` username and a password from the `volumes/grafana/admin_password`
file to login to the Grafana UI http://localhost:3000/.

Set up a cron job for periodical sensors execution. An example below will
collect the official AlmaLinux OS Docker image statistics every hour:

```
0 * * * * ${PROJECT_ROOT}/env/bin/python ${PROJECT_ROOT}/bin/docker_hub_stats_sensor.py -o library -i almalinux
```

For other sensors usage examples see their docstrings in code.


## Backups and maintenance

The `volumes/backup` directory is mounted to the `/srv/backup` in the InfluxDB
container, so you can use the following command to make a database backup:

```shell
UGID="$(id -u):$(id -g)" docker compose exec influxdb \
    influx backup /srv/backup/witness_backup.$(date '+%Y%m%d') -t "${INFLUX_ADMIN_TOKEN}"
```
