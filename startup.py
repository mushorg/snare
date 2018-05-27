import asyncio
import configparser
import pwd
import os
import aiohttp
import grp
from utils.versions_manager import VersionManager

class StartUp():
	def __init__(self, args):
		self.args = args
		
	def create_initial_config(self):
		cfg = configparser.ConfigParser()
		cfg['WEB-TOOLS'] = dict(google='', bing='')
		with open('/opt/snare/snare.cfg', 'w') as configfile:
			cfg.write(configfile)

	def snare_setup(self):
		if os.getuid() != 0:
			print('Snare has to be started as root!')
			sys.exit(1)
		# Create folders
		if not os.path.exists('/opt/snare'):
			os.mkdir('/opt/snare')
		if not os.path.exists('/opt/snare/pages'):
			os.mkdir('/opt/snare/pages')
		# Write pid to pid file
		with open('/opt/snare/snare.pid', 'wb') as pid_fh:
			pid_fh.write(str(os.getpid()).encode('utf-8'))
		# Config file
		if not os.path.exists('/opt/snare/snare.cfg'):
			create_initial_config()
		# Read or create the sensor id
		uuid_file_path = '/opt/snare/snare.uuid'
		if os.path.exists(uuid_file_path):
			with open(uuid_file_path, 'rb') as uuid_fh:
				snare_uuid = uuid_fh.read()
			return snare_uuid
		else:
			with open(uuid_file_path, 'wb') as uuid_fh:
				snare_uuid = str(uuid.uuid4()).encode('utf-8')
				uuid_fh.write(snare_uuid)
			return snare_uuid

	def drop_privileges(self):
		uid_name = 'nobody'
		wanted_user = pwd.getpwnam(uid_name)
		gid_name = grp.getgrgid(wanted_user.pw_gid).gr_name
		wanted_group = grp.getgrnam(gid_name)
		os.setgid(wanted_group.gr_gid)
		os.setuid(wanted_user.pw_uid)
		new_user = pwd.getpwuid(os.getuid())
		new_group = grp.getgrgid(os.getgid())
		print('privileges dropped, running as "{}:{}"'.format(new_user.pw_name, new_group.gr_name))

	def compare_version_info(self, timeout):
		while True:
			repo = git.Repo(os.getcwd())
			try:
				rem = repo.remote()
				res = rem.fetch()
				diff_list = res[0].commit.diff(repo.heads.master)
			except TimeoutError:
				print('timeout fetching the repository version')
			else:
				if diff_list:
					print('you are running an outdated version, SNARE will be updated and restarted')
					repo.git.reset('--hard')
					repo.heads.master.checkout()
					repo.git.clean('-xdf')
					repo.remotes.origin.pull()
					pip.main(['install', '-r', 'requirements.txt'])
					os.execv(sys.executable, [sys.executable, __file__] + sys.argv[1:])
					return
				else:
					print('you are running the latest version')
				time.sleep(timeout)

	async def check_tanner(self):
		vm = VersionManager()
		async with aiohttp.ClientSession() as client:
			req_url = 'http://{}:8090/version'.format(self.args.tanner)
			try:
				resp = await client.get(req_url)
				result = await resp.json()
				version = result["version"]
				vm.check_compatibility(version)
			except aiohttp.ClientOSError:
				print("Can't connect to tanner host {}".format(req_url))
				exit(1)
			else:
				await resp.release()
