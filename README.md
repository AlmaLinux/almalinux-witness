# almalinux-witness

The AlmaLinux OS Project monitoring tool.


## Deployment and initial configuration


### Pre-requirements

Create docker volume mount directories:

```shell
$ mkdir volumes/influxdb/data
$ mkdir volumes/mosquitto/{data,log}
```

Initialize a virtual environment:

```shell
$ virtualenv --system-site-packages env
$ . env/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
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


### Telegraf token creation

When you have the InfluxDB database initialized, you need to create an
unprivileged token for [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/).

Run InfluxDB CLI container in a separate terminal with the following command:

```shell
$ docker-compose run influxdb_cli bash
```

create a CLI configuration for the InfluxDB database:

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
$ BUCKET_ID=$(influx bucket list | grep -oP '^(\w+)(?=\s+distro_spread)')

# create authentication token
$ influx auth create --org AlmaLinux \
      --read-bucket "${BUCKET_ID}" --write-bucket "${BUCKET_ID}"
```

the last command will print a generated token and some additional information.
Create the `telegraf-vars.env` file in the project's root and put the
Telegraf token there:

```shell
INFLUX_TOKEN='ENTER_TELEGRAF_TOKEN_HERE'
```

Now you can safely terminate your main docker-compose process with the `Ctrl-c`
keyboard combination.


### Running the system

Execute the following command in order to launch InfluxDB, Mosquitto and
Telegraf:

```shell
$ docker compose up
```
