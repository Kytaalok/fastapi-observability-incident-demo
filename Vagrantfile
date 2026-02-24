Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.hostname = "obs-demo"

  config.vm.network "private_network", ip: "192.168.56.90"

  [
    { guest: 8000, host: 8000 }, # FastAPI
    { guest: 3000, host: 3000 }, # Grafana
    { guest: 9090, host: 9090 }, # Prometheus
    { guest: 3100, host: 3100 }  # Loki
  ].each do |port|
    config.vm.network "forwarded_port",
      guest: port[:guest],
      host: port[:host],
      host_ip: "127.0.0.1",
      auto_correct: true
  end

  config.vm.provider "virtualbox" do |vb|
    vb.name = "obs-demo"
    vb.memory = 4096
    vb.cpus = 2
  end

  config.vm.provision "shell", privileged: true, inline: <<-'SHELL'
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release

    install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    . /etc/os-release
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
      > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y \
      docker-ce \
      docker-ce-cli \
      containerd.io \
      docker-buildx-plugin \
      docker-compose-plugin

    systemctl enable --now docker
    usermod -aG docker vagrant || true

    cd /vagrant
    docker compose down || true
    docker compose up --build -d
  SHELL
end
