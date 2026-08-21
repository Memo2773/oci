import oci
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Ortam değişkenlerinden (environment variables) konfigürasyonu çek
config = {
    "user": os.getenv("OCI_USER_ID"),
    "key_content": os.getenv("OCI_PRIVATE_KEY"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION") # Mumbai için .env dosyasında "ap-mumbai-1" olmalı
}

try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Kimlik Dogrulamasi Basarili. Döngü baslatiliyor...")
except Exception as e:
    print(f"Kimlik Dogrulama Basarisiz: {e}")
    exit(1)

# Calistirma parametreleri
compartment_id = os.getenv("OCI_TENANCY_ID")
subnet_id = os.getenv("OCI_SUBNET_ID")
boot_volume_id = os.getenv("OCI_BOOT_VOLUME_ID") # YENİ: Eski diskinin OCID'si
public_ssh_key = os.getenv("OCI_PUBLIC_SSH_KEY")

# GÜVENLİK KONTROLÜ
if not public_ssh_key or public_ssh_key.strip() == "":
    print("KRITIK HATA: OCI_PUBLIC_SSH_KEY eksik veya bos!")
    exit(1)

# Sadece Mumbai AD-1 Bölgesi (Senin panelinde cikan AD)
ads = ["GiHR:AP-MUMBAI-1-AD-1"]

# Toplam deneme sayisi (60 az gelebilir, 2000 yapalim ki bütün gece denesin)
total_attempts = 2000 

for i in range(1, total_attempts + 1):
    current_ad = ads[0]
    print(f"[Deneme {i}/{total_attempts}] {current_ad} bölgesinde sunucu talep ediliyor...")

    try:
        request = oci.core.models.LaunchInstanceDetails(
            display_name="Kurtarilan-Sunucu",
            compartment_id=compartment_id,
            availability_domain=current_ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=2,          # YENİ ÜCRETSİZ LİMİT
                memory_in_gbs=12  # YENİ ÜCRETSİZ LİMİT
            ),
            # EN KRİTİK KISIM: İmaj yerine senin mevcut diskini bagliyoruz
            source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(
                source_type="bootVolume",
                boot_volume_id=boot_volume_id
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
                assign_private_dns_record=True,
                display_name="kurtarilan-vnic"
            ),
            metadata={
                "ssh_authorized_keys": str(public_ssh_key).strip()
            }
        )

        response = compute_client.launch_instance(request)
        if response.status == 200:
            print("BASARILI! Sunucu mukemmel bir sekilde olusturuldu.")
            exit(0)

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print("-> Kapasite Dolu. 60 saniye bekleniyor...")
        else:
            print(f"-> API Hatasi: {e.message}")

    if i < total_attempts:
        time.sleep(60) # Her deneme arasi 60 saniye bekler
