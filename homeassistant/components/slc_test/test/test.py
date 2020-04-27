import asyncio
import requests
import asyncio_dgram
import socket

host = "192.168.100.157"
port = 8080
try:
    url = "http://" + str(host) + ":" + str(port)
    my_response = requests.get(url).status_code
    if my_response == 200:
        print("есть контакт")
    else:
        print("нету")
except:
    print("unable to connect to Loxone")

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)
print("Your Computer Name is:" + hostname)
print("Your Computer IP Address is:" + IPAddr)


async def tomorrow():
    while True:
        await asyncio.sleep(1.0)


async def udp_echo_server():
    stream = await asyncio_dgram.bind(('127.0.1.1', 8888))
    print(f"Serving on {stream.sockname}")
    return stream


async def listen(stream):
    while True:
        data, remote_addr = await stream.recv()
        print(f"Echoing {data.decode()!r}")
        parsed_data = await parse_slc_data(data.decode())
        print(parsed_data)


async def parse_slc_data(data_string="DI:5:1"):
    event_dict = {}
    keys = ["Channel", "Number", "Value"]
    data_string = data_string.strip().split(':')
    if len(data_string) == 3:
        event_dict = dict(zip(keys, data_string))
    return event_dict


async def monitor(future, interval_seconds):
    while not future.done():
        # print("waiting...")
        await asyncio.sleep(interval_seconds)
    print("done!")

loop = asyncio.get_event_loop()

stream = udp_echo_server()



print (event.data)

async def start():
    tasks = []
    stream = await udp_echo_server()
    server_task = asyncio.create_task(listen(stream))
    tasks.append(server_task)
    tasks.append(asyncio.create_task(monitor(server_task, 1.0)))
    await asyncio.wait(tasks)


loop.run_until_complete(start())
