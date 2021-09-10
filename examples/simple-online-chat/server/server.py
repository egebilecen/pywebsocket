from classes.pywebsocket import WebsocketServer
from random import random
from urllib.parse import unquote
import json

# FUNCTIONS
def find_user_from_id(toFindUserID, user_list):
    for i, user in enumerate(user_list):
        if user["userID"] == toFindUserID:
            return (i, user)

def find_room_from_id(toFindRoomID, room_list):
    for i, room in enumerate(room_list):
        if room["roomID"] == toFindRoomID:
            return (i, room)

# HANDLERS
def setNickname(server, socket, data):
    if socket["data"]["isTakenNickname"]:
        return False
    
    socket["data"]["nickname"]        = data["nickname"]
    socket["data"]["isTakenNickname"] = True

    server.user_list.append({
        "userID"       : socket["data"]["userID"],
        "nickname"     : socket["data"]["nickname"],
        "data"         : socket["data"],
        "socket"       : socket
    })

def getRoomList(server, socket, data):
    dict = {
        "where" : "getRoomListResponse",
        "data"  : server.room_list
    }
    server.send_json(socket["id"], dict)

def newRoom(server, socket, data):
    if not socket["data"]["isCreatedRoom"]:
        room = {
            "roomID"      : random(),
            "roomName"    : data["roomName"],
            "ownerID"     : socket["data"]["userID"],
            "userList"    : [], # stored as nickname and user id pair
            "chatHistory" : []
        }

        server.room_list.append(room)

        socket["data"]["isCreatedRoom"] = True

        dict = {
            "where" : "newRoomResponse",
            "data"  : {"code":1, "roomID":room["roomID"]}
        }
        server.send_json(socket["id"], dict)

        dict2 = {
            "where" : "getRoomListResponse",
            "data"  : server.room_list
        }
        server.send_to_all(server.send_json, dict2)

    else:
        dict = {
            "where" : "newRoomResponse",
            "data"  : {"code":2}
        }
        server.send_json(socket["id"], dict)

def enterRoom(server, socket, data):
    for room in server.room_list:
        if room["roomID"] == data["roomID"]:
            if socket["data"]["currentRoomID"] is not room["roomID"]:
                room["userList"].append((socket["data"]["userID"], socket["data"]["nickname"]))

                dict = {
                    "where" : "enterRoomResponse",
                    "data"  : {"code":1, "room_name":room["roomName"],"room_user_list":room["userList"], "chat_history":room["chatHistory"]}
                }
                server.send_json(socket["id"], dict)
                
                socket["data"]["currentRoomID"] = room["roomID"]

                break

            else:
                dict = {
                    "where" : "enterRoomResponse",
                    "data"  : {"code":3}
                }
                server.send_json(socket["id"], dict) # already in chat room

        else:
            dict = {
                "where" : "enterRoomResponse",
                "data"  : {"code":2}
            }
            server.send_json(socket["id"], dict) # room is not exist

def chatNewMessage(server, socket, data):
    if socket["data"]["currentRoomID"] == data["roomID"]:
        for room in server.room_list:
            if room["roomID"] == socket["data"]["currentRoomID"]:
                room["chatHistory"].append({
                    "senderID"       : socket["data"]["userID"],
                    "senderNickname" : socket["data"]["nickname"],
                    "message"        : data["message"]
                })

                for user in server.user_list:
                    if user["data"]["currentRoomID"] == room["roomID"]:
                        dict = {
                            "where" : "chatNewMessageResponse",
                            "data"  : {
                                "senderID"       : socket["data"]["userID"],
                                "senderNickname" : socket["data"]["nickname"],
                                "message"        : data["message"]
                            }
                        }
                        server.send_json(user["socket"]["id"], dict)

    else: return False

# SPECIAL HANDLERS
def client_connect(server, socket):
    # create random id for socket user
    socket["data"]["userID"]          = random()
    socket["data"]["nickname"]        = None
    socket["data"]["isCreatedRoom"]   = False
    socket["data"]["isTakenNickname"] = False
    socket["data"]["currentRoomID"]   = None

def client_disconnect(server, socket):
    for i, user in enumerate(server.user_list):
        if socket["data"]["userID"] == user["userID"]:
            server.user_list.pop(i)

    if socket["data"]["currentRoomID"] is not None:
        for room in server.room_list:
            for i, user in enumerate(room["userList"]):
                if user[0] == socket["data"]["userID"]:
                    room["userList"].pop(i)
                    
                    if len(room["userList"]) < 1:
                        for j, _room in enumerate(server.room_list):
                            if _room["roomID"] == room["roomID"]:
                                server.room_list.pop(j)
                                dict = {
                                    "where" : "getRoomListResponse",
                                    "data"  : server.room_list
                                }
                                server.send_to_all(server.send_json, dict)
                            
def client_data(server, socket, data):
    # convert json string to dict
    json_data = json.loads(data)

    if json_data["where"] == "getRoomList":
        getRoomList(server, socket, json_data["data"])
    elif json_data["where"] == "newRoom":
        newRoom(server, socket, json_data["data"])
    elif json_data["where"] == "setNickname":
        setNickname(server, socket, json_data["data"])
    elif json_data["where"] == "enterRoom":
        enterRoom(server, socket, json_data["data"])
    elif json_data["where"] == "chatNewMessage":
        chatNewMessage(server, socket, json_data["data"])

server = WebsocketServer(port=3232, debug=True, pass_data_as_string=True)

server.set_special_handler("client_connect",    client_connect)
server.set_special_handler("client_disconnect", client_disconnect)
server.set_special_handler("client_data",       client_data)

server.user_list = []
server.room_list = []

server.start()
