import json
import time
import urllib.request
import urllib.parse
import urllib.error
import random

class MetaPublisher:
    def __init__(self, access_token: str = "", instagram_account_id: str = "", dry_run: bool = True, public_base_url: str = "https://raw.githubusercontent.com/thepeakiscold/pozitron-market/main"):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.dry_run = dry_run
        self.public_base_url = public_base_url.rstrip('/')
        self.graph_api_version = "v21.0"

    def configure(self, access_token: str = None, instagram_account_id: str = None, dry_run: bool = None, public_base_url: str = None):
        if access_token is not None:
            self.access_token = access_token
        if instagram_account_id is not None:
            self.instagram_account_id = instagram_account_id
        if dry_run is not None:
            self.dry_run = dry_run
        if public_base_url is not None:
            self.public_base_url = public_base_url.rstrip('/')

    def publish_post(self, post_data: dict) -> dict:
        """
        Publishes the post either in Live mode via Meta Graph API or in Dry-Run simulation mode.
        """
        full_caption = f"{post_data['caption']}\n\n{post_data['hashtags']}".strip()
        image_rel_url = post_data['image_url']
        
        # Determine public image URL
        if image_rel_url.startswith('http://') or image_rel_url.startswith('https://'):
            public_image_url = image_rel_url
        else:
            clean_path = image_rel_url.lstrip('./').lstrip('/')
            public_image_url = f"{self.public_base_url}/{clean_path}"

        # If dry run or missing credentials, simulate publishing
        if self.dry_run or not self.access_token or not self.instagram_account_id:
            mock_media_id = f"sim_ig_{int(time.time())}_{random.randint(100000, 999999)}"
            mock_code = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=11))
            mock_permalink = f"https://www.instagram.com/p/{mock_code}/"
            
            return {
                "success": True,
                "mode": "dry_run",
                "ig_media_id": mock_media_id,
                "ig_permalink": mock_permalink,
                "public_image_url": public_image_url,
                "caption_length": len(full_caption),
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%S")
            }

        # Live publishing via Meta Graph API
        try:
            # Step 1: Create Container
            container_url = f"https://graph.facebook.com/{self.graph_api_version}/{self.instagram_account_id}/media"
            container_payload = urllib.parse.urlencode({
                'image_url': public_image_url,
                'caption': full_caption,
                'access_token': self.access_token
            }).encode('utf-8')

            req = urllib.request.Request(container_url, data=container_payload, method='POST')
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_body = json.loads(resp.read().decode('utf-8'))
                creation_id = res_body.get('id')

            if not creation_id:
                return {"success": False, "error": f"Failed to get creation_id from Meta API: {res_body}"}

            # Step 2: Poll container status if needed (wait 2s)
            time.sleep(2)

            # Step 3: Publish Container
            publish_url = f"https://graph.facebook.com/{self.graph_api_version}/{self.instagram_account_id}/media_publish"
            publish_payload = urllib.parse.urlencode({
                'creation_id': creation_id,
                'access_token': self.access_token
            }).encode('utf-8')

            req_pub = urllib.request.Request(publish_url, data=publish_payload, method='POST')
            with urllib.request.urlopen(req_pub, timeout=30) as resp_pub:
                pub_res = json.loads(resp_pub.read().decode('utf-8'))
                media_id = pub_res.get('id')

            if not media_id:
                return {"success": False, "error": f"Failed to publish media on Meta API: {pub_res}"}

            # Step 4: Fetch permalink
            permalink = f"https://www.instagram.com/p/{media_id}/"
            try:
                info_url = f"https://graph.facebook.com/{self.graph_api_version}/{media_id}?fields=permalink&access_token={self.access_token}"
                with urllib.request.urlopen(info_url, timeout=10) as resp_info:
                    info_res = json.loads(resp_info.read().decode('utf-8'))
                    permalink = info_res.get('permalink', permalink)
            except Exception:
                pass

            return {
                "success": True,
                "mode": "live",
                "ig_media_id": media_id,
                "ig_permalink": permalink,
                "public_image_url": public_image_url,
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%S")
            }

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8')
            try:
                err_json = json.loads(err_msg)
                err_msg = err_json.get('error', {}).get('message', err_msg)
            except Exception:
                pass
            return {"success": False, "error": f"Meta Graph API HTTP {e.code}: {err_msg}"}
        except Exception as ex:
            return {"success": False, "error": f"Publish exception: {str(ex)}"}
