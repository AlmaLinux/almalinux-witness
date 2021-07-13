# almalinux-witness

The AlmaLinux OS Project monitoring tool.


## Deployment and initial configuration


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

Enable masquerading:

```shell
$ firewall-cmd --zone=public --add-masquerade --permanent
$ firewall-cmd --reload
```

### InfluxDB database initialization

First, you need to initialize the InfluxDB database (don't forget to either
define corresponding environment variables or replace them with desired
values):

```shell
docker-compose run \
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
for your InfluxDB administration purposes.

Wait until you will see the following log messages on your console:

```
2021-06-09T21:10:26.686975Z     info    Listening       {"log_id": "0UdedM~W000", "service": "tcp-listener", "transport": "http", "addr": ":8086", "port": 8086}
2021-06-09T21:10:26.687147Z     info    Starting        {"log_id": "0UdedM~W000", "service": "telemetry", "interval": "8h"}
```

then terminate the docker-compose process with `Ctrl-c`.


### Telegraf token creation

When you have the InfluxDB database initialized, you need to create an
unprivileged token for [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/).

Run docker-compose with the `influx_admin` profile enabled:

```shell
$ docker-compose --profile=influx_admin up
```

Open a separate terminal and connect to the `influxdb_cli` container:

```shell
$ docker-compose exec influxdb_cli bash
```

then create a CLI configuration for the InfluxDB database:

```shell
$ influx config create --active -n dbadmin \
      -u http://influxdb:8086 -t '${INFLUX_ADMIN_TOKEN}' -o AlmaLinux
```

that will create the `dbadmin` configuration for the `AlmaLinux` organization
authenticating using the administrator token.

Now you need to create an authentication token for Telegraf, that token must
have read/write permissions for the `distro_spread` bucket:

```shell
# get the "distro_spread" bucket ID
$ BUCKET_ID=$(influx bucket list -t '${INFLUX_ADMIN_TOKEN}' | grep -oP '^(\w+)(?=\s+distro_spread)')

# create authentication token
$ influx auth create --org AlmaLinux \
      --read-bucket "${BUCKET_ID}" --write-bucket "${BUCKET_ID}" -t '${INFLUX_ADMIN_TOKEN}'
```

the last command will print a generated token and some additional information.
Create the `telegraf-vars.env` file in the project's root and put the
Telegraf token there:

```shell
INFLUX_TOKEN='ENTER_TELEGRAF_TOKEN_HERE'
```

Now you can safely terminate both your docker-compose processess with the
`Ctrl-c` keyboard combination.


### Grafana configuration

Configure a Grafana administrator password:

```shell
$ echo 'ENTER_PASSWORD_HERE' > volumes/grafana/admin_password
$ chmod 600 volumes/grafana/admin_password
```

### Running the system

Execute the following command in order to launch InfluxDB, Mosquitto and
Telegraf:

```shell
$ docker-compose up
```
