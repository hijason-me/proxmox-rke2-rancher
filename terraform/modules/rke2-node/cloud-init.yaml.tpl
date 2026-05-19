#cloud-config
hostname: ${hostname}
package_update: true
packages:
  - curl
  - open-iscsi
  - nfs-common
  - qemu-guest-agent

runcmd:
  - systemctl enable --now qemu-guest-agent
  - mkdir -p /etc/rancher/rke2

  # Write RKE2 config
  - |
    cat > /etc/rancher/rke2/config.yaml << 'EOF'
    token: ${rke2_token}
    %{ if rke2_role == "server" ~}
    %{ if rke2_server_url != "" ~}
    server: ${rke2_server_url}
    %{ endif ~}
    tls-san:
    %{ for san in rke2_sans ~}
      - ${san}
    %{ endfor ~}
    %{ else ~}
    server: ${rke2_server_url}
    %{ endif ~}
    %{ if length(node_labels) > 0 ~}
    node-label:
    %{ for k, v in node_labels ~}
      - "${k}=${v}"
    %{ endfor ~}
    %{ endif ~}
    %{ if length(node_taints) > 0 ~}
    node-taint:
    %{ for taint in node_taints ~}
      - "${taint}"
    %{ endfor ~}
    %{ endif ~}
    EOF

  # Install RKE2
  - curl -sfL https://get.rke2.io | INSTALL_RKE2_VERSION="${rke2_version}" INSTALL_RKE2_TYPE="${rke2_role}" sh -

  # Enable and start RKE2
  - systemctl enable rke2-${rke2_role}
  - systemctl start rke2-${rke2_role}

final_message: "RKE2 ${rke2_role} node ${hostname} setup complete after $UPTIME seconds"
