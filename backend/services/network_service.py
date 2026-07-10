import socket


class NetworkService:
    
    def get_client_ip(self, request):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "127.0.0.1" 

    def get_client_mac(self, ip_address):
        try:
            with open("/proc/net/arp", "r") as arp_table:
                for line in arp_table:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip_address:
                        return parts[3].upper()
        except FileNotFoundError:
            pass

        return "00:00:00:00:00:00"

    def get_hostname(self, ip_address):
        try:
            return socket.gethostbyaddr(ip_address)[0]
        except socket.herror:
            return "Unknown"
