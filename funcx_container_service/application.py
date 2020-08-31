from flask import Flask
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)


class Environments(Resource):
    def get(self):
        return "TODO :)"

api.add_resource(Environments, "/environments")


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000)
