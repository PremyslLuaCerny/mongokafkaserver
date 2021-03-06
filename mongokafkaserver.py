import aiokafka
import configparser
import motor.motor_asyncio
import pymongo
import time

import aiohttp

from rattlepy import rattlepy


class MyServerApplication(rattlepy.RattlePyApplication):

	def __init__(self):
		super().__init__()

		cfg = configparser.ConfigParser()
		cfg.read('./production-site.conf')

		# Initialize MongoDBClient
		self.MongoDBClient = motor.motor_asyncio.AsyncIOMotorClient(
			host=cfg.get('mongodb', 'url'),
			port=27017,
			driver=pymongo.driver_info.DriverInfo(name="rattlepy.MongoDBClient", platform="rattlepy"),
			io_loop=self.Loop
		)

		# Initialize KafkaProducer
		self.KafkaProducer = aiokafka.AIOKafkaProducer(
			bootstrap_servers=cfg.get('kafka', 'url'),
			loop=self.Loop
		)

	def prepare_routes(self):
		"""
		Register custom routes.
		:return:
		"""
		self.Routes.append(aiohttp.web.post("/post", self.post))

	async def post(self, request):
		"""
		Post a JSON document into MongoDB and Kafka in asynchronous loop.
		:param request: request
		:return: response
		"""

		document = await request.json()

		collection_name = str(time.time() / 3600)
		mongodb_collection = self.MongoDBClient.Client["documents"][collection_name]
		await mongodb_collection.insert_one(document)

		await self.KafkaProducer.start()
		await self.KafkaProducer.send_and_wait("post-documents", document)
		await self.KafkaProducer.stop()

		return aiohttp.web.json_response({"OK": 1})


if __name__ == '__main__':
	app = MyServerApplication()
	app.serve()
