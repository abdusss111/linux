#==============================================================================
# Terraform Configuration for Dapmeet Infrastructure
# Bonus Task 2: Infrastructure as Code for VM Provisioning
#==============================================================================
# This configuration creates:
# - VM1: Frontend server (Next.js, Nginx)
# - VM2: Backend server (FastAPI, PostgreSQL)
# - Network infrastructure (VPC, Subnets, Security Groups)
#==============================================================================

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.100"
    }
  }

  # Optional: Remote state storage
  # backend "s3" {
  #   endpoint   = "storage.yandexcloud.net"
  #   bucket     = "dapmeet-terraform-state"
  #   key        = "infrastructure/terraform.tfstate"
  #   region     = "ru-central1"
  #   skip_region_validation      = true
  #   skip_credentials_validation = true
  # }
}

#------------------------------------------------------------------------------
# Provider Configuration
#------------------------------------------------------------------------------

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.yc_cloud_id
  folder_id = var.yc_folder_id
  zone      = var.yc_zone
}

#------------------------------------------------------------------------------
# Data Sources
#------------------------------------------------------------------------------

# Get latest Ubuntu 22.04 LTS image
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

#------------------------------------------------------------------------------
# Network Resources
#------------------------------------------------------------------------------

# Virtual Private Cloud
resource "yandex_vpc_network" "dapmeet_network" {
  name        = "${var.project_name}-network"
  description = "VPC network for Dapmeet project"
}

# Subnet for VMs
resource "yandex_vpc_subnet" "dapmeet_subnet" {
  name           = "${var.project_name}-subnet"
  description    = "Subnet for Dapmeet VMs"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.dapmeet_network.id
  v4_cidr_blocks = [var.subnet_cidr]
}

#------------------------------------------------------------------------------
# Security Groups
#------------------------------------------------------------------------------

# Security group for Frontend VM
resource "yandex_vpc_security_group" "frontend_sg" {
  name        = "${var.project_name}-frontend-sg"
  description = "Security group for frontend VM"
  network_id  = yandex_vpc_network.dapmeet_network.id

  # SSH access
  ingress {
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = var.ssh_allowed_ips
    description    = "SSH access"
  }

  # HTTP
  ingress {
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "HTTP access"
  }

  # HTTPS
  ingress {
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "HTTPS access"
  }

  # Next.js dev server
  ingress {
    protocol       = "TCP"
    port           = 3000
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "Next.js application"
  }

  # All outbound traffic
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "Allow all outbound traffic"
  }
}

# Security group for Backend VM
resource "yandex_vpc_security_group" "backend_sg" {
  name        = "${var.project_name}-backend-sg"
  description = "Security group for backend VM"
  network_id  = yandex_vpc_network.dapmeet_network.id

  # SSH access
  ingress {
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = var.ssh_allowed_ips
    description    = "SSH access"
  }

  # FastAPI
  ingress {
    protocol       = "TCP"
    port           = 8000
    v4_cidr_blocks = [var.subnet_cidr]
    description    = "FastAPI backend (internal)"
  }

  # PostgreSQL (internal only)
  ingress {
    protocol       = "TCP"
    port           = 5432
    v4_cidr_blocks = [var.subnet_cidr]
    description    = "PostgreSQL (internal)"
  }

  # All outbound traffic
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "Allow all outbound traffic"
  }
}

#------------------------------------------------------------------------------
# SSH Key
#------------------------------------------------------------------------------

resource "yandex_compute_disk" "boot_disk_vm1" {
  name     = "${var.project_name}-frontend-boot"
  zone     = var.yc_zone
  image_id = data.yandex_compute_image.ubuntu.id
  size     = var.vm_disk_size
  type     = "network-ssd"
}

resource "yandex_compute_disk" "boot_disk_vm2" {
  name     = "${var.project_name}-backend-boot"
  zone     = var.yc_zone
  image_id = data.yandex_compute_image.ubuntu.id
  size     = var.vm_disk_size
  type     = "network-ssd"
}

#------------------------------------------------------------------------------
# VM1 - Frontend Server
#------------------------------------------------------------------------------

resource "yandex_compute_instance" "vm1_frontend" {
  name        = "${var.project_name}-frontend"
  hostname    = "vm1-frontend"
  description = "Frontend VM - Next.js and Nginx"
  zone        = var.yc_zone
  platform_id = var.vm_platform_id

  resources {
    cores         = var.frontend_cores
    memory        = var.frontend_memory
    core_fraction = var.vm_core_fraction
  }

  boot_disk {
    disk_id = yandex_compute_disk.boot_disk_vm1.id
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.dapmeet_subnet.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.frontend_sg.id]
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    
    user-data = templatefile("${path.module}/cloud-init/frontend.yaml", {
      ssh_user     = var.ssh_user
      project_name = var.project_name
      timezone     = var.timezone
    })
  }

  scheduling_policy {
    preemptible = var.use_preemptible
  }

  labels = {
    project     = var.project_name
    environment = var.environment
    role        = "frontend"
    managed_by  = "terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}

#------------------------------------------------------------------------------
# VM2 - Backend Server
#------------------------------------------------------------------------------

resource "yandex_compute_instance" "vm2_backend" {
  name        = "${var.project_name}-backend"
  hostname    = "vm2-backend"
  description = "Backend VM - FastAPI, PostgreSQL"
  zone        = var.yc_zone
  platform_id = var.vm_platform_id

  resources {
    cores         = var.backend_cores
    memory        = var.backend_memory
    core_fraction = var.vm_core_fraction
  }

  boot_disk {
    disk_id = yandex_compute_disk.boot_disk_vm2.id
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.dapmeet_subnet.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.backend_sg.id]
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    
    user-data = templatefile("${path.module}/cloud-init/backend.yaml", {
      ssh_user       = var.ssh_user
      project_name   = var.project_name
      timezone       = var.timezone
      db_password    = var.db_password
      frontend_ip    = yandex_compute_instance.vm1_frontend.network_interface[0].ip_address
    })
  }

  scheduling_policy {
    preemptible = var.use_preemptible
  }

  labels = {
    project     = var.project_name
    environment = var.environment
    role        = "backend"
    managed_by  = "terraform"
  }

  depends_on = [yandex_compute_instance.vm1_frontend]

  lifecycle {
    create_before_destroy = true
  }
}

#------------------------------------------------------------------------------
# Static IP Addresses (Optional)
#------------------------------------------------------------------------------

resource "yandex_vpc_address" "frontend_ip" {
  count = var.reserve_static_ip ? 1 : 0
  name  = "${var.project_name}-frontend-ip"
  
  external_ipv4_address {
    zone_id = var.yc_zone
  }
}

#------------------------------------------------------------------------------
# DNS Records (Optional - if using Yandex DNS)
#------------------------------------------------------------------------------

# resource "yandex_dns_recordset" "frontend" {
#   count   = var.create_dns_records ? 1 : 0
#   zone_id = var.dns_zone_id
#   name    = var.domain_name
#   type    = "A"
#   ttl     = 300
#   data    = [yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address]
# }

