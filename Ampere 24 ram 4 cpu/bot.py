import oci
import os
import time
import urllib.request
import urllib.parse

def get_env_var(name, default_value=""):
    val = os.environ.get(name)
    if val is None:
        print(f"HATA: {name} ortam degiskeni bulunamadi!")
        return default_value
    return val.strip()

telegram_token = get_env_var("TELEGRAM_BOT_TOKEN")
telegram_chat_id = get_env_var("TELEGRAM_CHAT_ID")

# Telegram Mesaj Gonderme Fonksiyonu
def send_telegram_message(message):
    if telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        data = urllib.parse.urlencode({'chat_id': telegram_chat_id, 'text': message}).encode('utf-8')
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=data))
        except Exception as e:
            print(f"Telegram mesaji gonderilemedi: {e}")

config = {
    "user": get_env_var("OCI_USER_ID"),
    "key_content": get_env_var("OCI_PRIVATE_KEY"),
    "fingerprint": get_env_var("OCI_FINGERPRINT"),
    "tenancy": get_env_var("OCI_TENANCY_ID"),
    "region": get_env_var("OCI_REGION", "ap-mumbai-1")
}

try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Kimlik Dogrulamasi Basarili.")
except Exception as e:
    print(f"Kimlik Dogrulama Basarisiz: {e}")
    exit(1)

compartment_id = get_env_var("OCI_TENANCY_ID")
subnet_id = get_env_var("OCI_SUBNET_ID")
boot_volume_id = get_env_var("OCI_BOOT_VOLUME_ID")
public_ssh_key = get_env_var("OCI_PUBLIC_SSH_KEY")

if not boot_volume_id or not subnet_id:
    print("KRITIK HATA: OCI_BOOT_VOLUME_ID veya OCI_SUBNET_ID eksik!")
    exit(1)

ads = ["GiHR:AP-MUMBAI-1-AD-1"]
total_attempts = 2000 
sleep_time = 150 # Her deneme arasi beklenecek saniye

# Bot calismaya basladiginda haber ver
send_telegram_message("🚀 Oracle Bildirim Botu Aktif!\nMumbai bölgesinde kapasite aranmaya başlandı. Sunucu bulunduğunda sana hemen haber vereceğim.")

for i in range(1, total_attempts + 1):
    current_ad = ads[0]
    print(f"[Deneme {i}/{total_attempts}] Sunucu talep ediliyor...")

    try:
        request = oci.core.models.LaunchInstanceDetails(
            display_name="Kurtarilan-Sunucu",
            compartment_id=compartment_id,
            availability_domain=current_ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
            source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(source_type="bootVolume", boot_volume_id=boot_volume_id),
            create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=subnet_id, assign_public_ip=True, assign_private_dns_record=True, display_name="kurtarilan-vnic"),
            metadata={"ssh_authorized_keys": public_ssh_key}
        )

        response = compute_client.launch_instance(request)
        if response.status == 200:
            msg = "🎉 MÜJDE!\nOracle sunucusu başarıyla kuruldu ve eski diskin bağlandı! Hemen panele girip kontrol edebilirsin."
            print(msg)
            send_telegram_message(msg)
            exit(0)

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print("-> Kapasite Dolu.")
        else:
            print(f"-> API Hatasi: {e.message}")

    # Eger 2 saat (120 deneme) gectiyse bilgilendirme yap
    if i % 300 == 0:
        send_telegram_message(f"⏳ Bilgilendirme:\nTam 2 saat geçti ve {i} deneme yapıldı. Mumbai'de hala boş yer yok ancak bot arka planda pes etmeden aramaya devam ediyor.")

    if i < total_attempts:
        time.sleep(sleep_time)
        
