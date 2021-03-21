from flask import Flask, request, Request, abort, send_file, jsonify, render_template
from flask_caching import Cache
from json import loads, dumps
import socket
from hashlib import sha1

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 60})


@app.route("/", methods=["GET", "POST"])
def check_view():
    if request.method == "POST":
        files = ["player", "multiplayer", "server"]
        needles = {
            "player": ["Miscellaneous.WebUI port"],
            "multiplayer": [
                "Multiplayer General Options.HTTP Server Port",
                "Multiplayer General Options.Simulation Port",
            ],
            "server": ["port"],
        }
        host = request.form.get("host")
        if not host:
            abort(400)

        sha1_hash = sha1()
        sha1_hash.update(host.encode("utf-8"))
        hash_key = str(sha1_hash.hexdigest())
        if cache.get(hash_key) is None:
            print("New  host: " + hash_key)
        else:
            print("Using cached result: " + hash_key)
            return render_template("results.html", results=loads(cache.get(hash_key)))

        results = {}
        for file in files:
            upload_file = (
                request.files[file]
                if file in request.files
                and request.files[file].content_type == "application/json"
                else None
            )
            if upload_file:
                results[file] = {}
                got = upload_file.stream.read()
                json = loads(got)
                file_needles = needles[file]

                for raw_needle in file_needles:
                    needle = raw_needle.split(".")
                    value = None
                    if len(needle) == 1:
                        value = json[needle[0]]
                    if len(needle) == 2:
                        sub_needle = needle[1]
                        value = json[needle[0]][sub_needle]
                        if sub_needle == "HTTP Server Port":
                            results[file][raw_needle + "UDP"] = {
                                "port": value,
                                "orig_name": raw_needle,
                                "result": None,
                                "type": "udp",
                            }
                        if sub_needle == "Simulation Port":
                            for i in range(1, 3):
                                results[file][raw_needle + "UDP" + str(i)] = {
                                    "port": int(value) + i,
                                    "result": None,
                                    "type": "udp",
                                    "orig_name": raw_needle,
                                }
                    results[file][raw_needle] = {
                        "port": value,
                        "result": None,
                        "type": "tcp",
                        "orig_name": raw_needle,
                    }

        # do port check
        for file, result in results.items():
            for needle, value in result.items():
                port_to_check = value["port"]
                type = value["type"]
                sock = None
                result = None
                try:
                    if type == "tcp":
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    else:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    result = sock.connect_ex((host, port_to_check))
                    sock.close()
                except:
                    result = 1

                results[file][needle]["result"] = result == 0
        # set cache
        cache.set(hash_key, dumps(results))
        return render_template("results.html", results=results)
    return render_template("form.html")


app.run(
    host="localhost",
    port="5001",
    debug=False,
)