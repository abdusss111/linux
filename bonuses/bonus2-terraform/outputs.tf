#==============================================================================
# Terraform Outputs for Dapmeet Infrastructure
#==============================================================================

#------------------------------------------------------------------------------
# Network Information
#------------------------------------------------------------------------------

output "network_id" {
  description = "ID of the VPC network"
  value       = yandex_vpc_network.dapmeet_network.id
}

output "subnet_id" {
  description = "ID of the subnet"
  value       = yandex_vpc_subnet.dapmeet_subnet.id
}

output "subnet_cidr" {
  description = "CIDR block of the subnet"
  value       = yandex_vpc_subnet.dapmeet_subnet.v4_cidr_blocks[0]
}

#------------------------------------------------------------------------------
# Frontend VM Information
#------------------------------------------------------------------------------

output "frontend_vm_id" {
  description = "ID of the frontend VM"
  value       = yandex_compute_instance.vm1_frontend.id
}

output "frontend_internal_ip" {
  description = "Internal IP address of the frontend VM"
  value       = yandex_compute_instance.vm1_frontend.network_interface[0].ip_address
}

output "frontend_external_ip" {
  description = "External (public) IP address of the frontend VM"
  value       = yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address
}

output "frontend_fqdn" {
  description = "FQDN of the frontend VM"
  value       = yandex_compute_instance.vm1_frontend.fqdn
}

#------------------------------------------------------------------------------
# Backend VM Information
#------------------------------------------------------------------------------

output "backend_vm_id" {
  description = "ID of the backend VM"
  value       = yandex_compute_instance.vm2_backend.id
}

output "backend_internal_ip" {
  description = "Internal IP address of the backend VM"
  value       = yandex_compute_instance.vm2_backend.network_interface[0].ip_address
}

output "backend_external_ip" {
  description = "External (public) IP address of the backend VM"
  value       = yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address
}

output "backend_fqdn" {
  description = "FQDN of the backend VM"
  value       = yandex_compute_instance.vm2_backend.fqdn
}

#------------------------------------------------------------------------------
# SSH Connection Commands
#------------------------------------------------------------------------------

output "ssh_frontend" {
  description = "SSH command to connect to frontend VM"
  value       = "ssh ${var.ssh_user}@${yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address}"
}

output "ssh_backend" {
  description = "SSH command to connect to backend VM"
  value       = "ssh ${var.ssh_user}@${yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address}"
}

#------------------------------------------------------------------------------
# Application URLs
#------------------------------------------------------------------------------

output "frontend_url" {
  description = "URL to access the frontend application"
  value       = "http://${yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address}:3000"
}

output "backend_api_url" {
  description = "URL to access the backend API"
  value       = "http://${yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address}:8000"
}

#------------------------------------------------------------------------------
# Ansible Inventory
#------------------------------------------------------------------------------

output "ansible_inventory" {
  description = "Ansible inventory configuration"
  value       = <<-EOT
    # Generated Ansible inventory
    # Copy this to your sis5/ansible/inventory/hosts.yml
    
    ---
    all:
      children:
        frontend:
          hosts:
            vm1:
              ansible_host: ${yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address}
              ansible_user: ${var.ssh_user}
        backend:
          hosts:
            vm2:
              ansible_host: ${yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address}
              ansible_user: ${var.ssh_user}
      vars:
        ansible_python_interpreter: /usr/bin/python3
        project_name: ${var.project_name}
        domain_name: ${var.domain_name}
  EOT
}

#------------------------------------------------------------------------------
# Summary
#------------------------------------------------------------------------------

output "summary" {
  description = "Infrastructure summary"
  value       = <<-EOT
    
    ╔════════════════════════════════════════════════════════════════════╗
    ║                  DAPMEET INFRASTRUCTURE SUMMARY                    ║
    ╠════════════════════════════════════════════════════════════════════╣
    ║  Environment: ${var.environment}                                   
    ║  Region: ${var.yc_zone}                                            
    ╠════════════════════════════════════════════════════════════════════╣
    ║  VM1 (Frontend)                                                    
    ║    - Internal IP: ${yandex_compute_instance.vm1_frontend.network_interface[0].ip_address}
    ║    - External IP: ${yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address}
    ║    - Resources: ${var.frontend_cores} cores, ${var.frontend_memory}GB RAM
    ║    - URL: http://${yandex_compute_instance.vm1_frontend.network_interface[0].nat_ip_address}:3000
    ╠════════════════════════════════════════════════════════════════════╣
    ║  VM2 (Backend)                                                     
    ║    - Internal IP: ${yandex_compute_instance.vm2_backend.network_interface[0].ip_address}
    ║    - External IP: ${yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address}
    ║    - Resources: ${var.backend_cores} cores, ${var.backend_memory}GB RAM
    ║    - API URL: http://${yandex_compute_instance.vm2_backend.network_interface[0].nat_ip_address}:8000
    ╚════════════════════════════════════════════════════════════════════╝
    
    Next Steps:
    1. Update Ansible inventory with the generated configuration
    2. Run: ansible-playbook -i inventory/hosts.yml playbooks/site.yml
    3. Access frontend at the URL shown above
    
  EOT
}

