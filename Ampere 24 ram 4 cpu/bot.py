import oci
import os
import time

# Degiskenleri guvenli cekmek icin yardimci fonksiyon (NoneType hatasini onler)
def get_env_var(name, default_value=""):
    val = os.environ.get(name)
    if val is None:
        print(f"HATA: {name} ortam degiskeni GitHub tarafindan Python'a aktarilamadi!")
        return default_value
    return val.strip()

config = {
    "user": get_env_var("OCI_USER_ID"),
    "key_content": get_env_var("OCI_PRIVATE_KEY"),
    "fingerprint": get_env_var("OCI_FINGERPRINT"),
    "tenancy": get_env_var("OCI_TENANCY_ID"),
    "region": get_env_var("OCI_REGION", "ap-mumbai-1")
}

try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Kimlik Dogrulamasi Basarili. Degiskenler kontrol ediliyor...")
except Exception as e:
    print(f"Kimlik Dogrulama Basarisiz: {e}")
    exit(1)

compartment_id = get_env_var("OCI_TENANCY_ID")
subnet_id = get_env_var("OCI_SUBNET_ID")
boot_volume_id = get_env_var("OCI_BOOT_VOLUME_ID")
public_ssh_key = get_env_var("OCI_PUBLIC_SSH_KEY")

# Kritik degiskenlerin bos olup olmadigini kontrol et
if not boot_volume_id:
    print("KRITIK HATA: OCI_BOOT_VOLUME_ID eksik!")
    exit(1)
if not subnet_id:
    print("KRITIK HATA: OCI_SUBNET_ID eksik! Ag bileseni (Subnet) olmadan sunucu kurulamaz.")
    exit(1)

ads = ["GiHR:AP-MUMBAI-1-AD-1"]
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
                ocpus=2,
                memory_in_gbs=12
            ),
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
                "ssh_authorized_keys": public_ssh_key
            }
        )

        response = compute_client.launch_instance(request)
        if response.status == 200:
            print("BASARILI! Sunucu mukemmel bir sekilde olusturuldu.")
            exit(0)

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print("-> Kapasite Dolu. 120 saniye bekleniyor...")
        else:
            print(f"-> API Hatasi: {e.message}")

    if i < total_attempts:
        time.sleep(120)
        
