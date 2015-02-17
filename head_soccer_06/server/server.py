__author__ = 'newtonis'

import threading
from PodSixNet.Server import Server
from PodSixNet.Channel import Channel
from PodSixNet.ServerUDP import ServerUDP
from source.gui.getCenter import GetCenter
from game import *
from database import serverQ
import opinion
from source.data.images import Heads
from source.data import config
import random

class ServerChannel(Channel):
    def __init__(self , *args, **kwargs):
        Channel.__init__(self, *args, **kwargs)
        self.id = str(self._server.NextId())
        self.status = "checkData"
        self.ip = "nn"
        self.conn = "nn"
        self.name = "noName"
        self.head = Heads.heads[random.randrange(len(Heads.heads))]

        self.RoomDef = None
        #### UDP ####
        self.udpAddr = -1

    #### UDP def ###
    def SendUDP(self,data):
        #print data,"sent in udp",self.udpAddr
        if self.udpAddr != -1:
            self._server.UDPconnector.Send(data,self.udpAddr)
    def Close(self):
        print "Player",self.GetID(),"has left the game"
        if self.RoomDef:
            self.RoomDef(self,"lost")
        self._server.HandlePlayerLost(self)
    def Network_request_basic(self,data):
        print "Player",self.GetID(),"has decided to request basic information"
        self.SendBasic()
    def Network_request_basicUDP(self,data):
        print "request basic udp"
        self.SendBasicUDP()
    def Network_request_rooms(self,data):
        if self.status == "checkData":
            print "Player",self.GetID()," has decided to join the game"
            allow , reason = self._server.AllowEntrance()
            if allow:
                if serverQ.CheckOpinionNeed(self.ip):
                    print "Opinion survey sent to player"
                    self.SendOpinion()
                else:
                    self.SendSkip()
                    print "No opinion survey needed"
                    print "Sending name request"
                    self.SendRequestName()

                    #self.SendRooms()
            else:
                print "However the server is full so the player will be rejected"
                self.SendNotAllow(reason)
        elif self.status == "already-connected":
            print "Player",self.GetID(),"requested rooms again"
            self.SendRooms()
    def Network_get_opinion(self,data):
        print "Player",self.GetID(),"opinion has arrived"
        if data["option"] >= len(self.opinion["options"]):
            print "Opinion corrupted!",data["option"]
        else:
            print self.opinion["question"]
            print "He has elected '"+self.opinion["options"][data["option"]]+"'"
            serverQ.AddOpinion(self.ip,self.opinion["id"],data["option"])
        self.SendRequestName()
    def Network_send_name(self,data):
        print "Player ",self.GetID(),"is now named '"+str(data["name"])+"'"
        allowed_name = True
        error = ""
        for x in self._server.clients.keys():
            if self._server.clients[x].name == data["name"]:
                allowed_name = False
                error = "Name already in use"
        if len(data["name"]) < 4:
            allowed_name = False
            error  = "Name too short"
        if allowed_name:
            self.name = data["name"]
            self.SendRooms()
        else:
            self.Send({"action":"name_error","error":error})
    def Network_join_game(self,data):
        print "Player",self.GetID(),"want to join to room",data["room_name"]
        self._server.JoinPlayer(self,data["room_name"])
    def Network_exit_game(self,data):
        self.RoomDef(self,"exit",data)
    def Network_req_av_players(self,data):
        print "Player",self.GetID(),"requested players available"
        self.Send({"action":"data_players","players":self._server.GetPlayers(),"player-name":self.name})
    def Network_set_configuration(self,data):
        error = ""
        if data["name"] != None:
            for x in self._server.clients.keys():
                if self._server.clients[x].name == data["name"]:
                    error = "Name already in use"
            if len(data["name"]) < 4:
                error = "Name too short"
        else:
            data["name"] = self.name
        if error == "":
            print "Player",self.GetID(),"has just changed his/her name to",data["name"]
            self.name = data["name"]
        self.head = data["headcode"]
        self.Send({"action":"profile_conf_error","error":error})
    def Network_joinA(self,data):
        self.RoomDef(self,"joinA",data)
    def Network_joinB(self,data):
        self.RoomDef(self,"joinB",data)
    def Network_spectate(self,data):
        self.RoomDef(self,"spectate",data)
    def Network_keys(self,data):
        self.RoomDef(self,"keys",data)
    def Network_update_pos(self,data):
        self.RoomDef(self,"update_pos",data)
    def Network_bc(self,data):
        self.RoomDef(self,"bc",data)
    def SetRoomDef(self,func):
        print "room def set"
        self.RoomDef = func
    def SendBasic(self):
        self.Send({"action":"basic_data","info":self._server.GetBasicInfo(),"id":self.id})
    def SendBasicUDP(self):
        self.SendUDP({"action":"udp_signal"})
    def SendRooms(self):
        self.status = "already-connected"
        self.Send({"action":"rooms_data","info":self._server.GetRoomsData()})
    def SendNotAllow(self,reason):
        self.Send({"action":"not_allowed","reason":reason})
    def SendOpinion(self):
        self.opinion = opinion.Random()
        self.Send({"action":"opinion","content":self.opinion})
    def SendSkip(self):
        self.Send({"action":"skip_opinion"})
    def SendRequestName(self):
        self.Send({"action":"request_name"})
    def GetID(self):
        if self.name != "noName":
            return "'"+str(self.name)+"'"
        else:
            return self.id

class WhiteboardServer(Server):
    channelClass = ServerChannel
    def __init__(self,*args,**kwargs):
        Server.__init__(self,*args,**kwargs)
        print "Starting server..."

        ##### START UDP #####
        self.UDPconnector = ServerUDP(*args,**kwargs)
        self.UDPconnector.SetTarget(self)
        self.UDPconnector.SetPing(config.ping_server)

        self.id = 0
        self.mode = "Quickmatchs server"
        self.max_players = 10
        self.name = "Newtonis's server"
        self.clients = dict()
        self.players = dict()
        self.gameWorlds = dict()
        self.dictOrder = []

        self.play = True
        self.commandsThread = threading.Thread(target=self.CommandThreadDef,name="Commands thread")
        self.commandsThread.start()
        self.Add5Rooms()

    ##### UDP DEF #####
    def Network_UDP_data(self,data,addr):
        if not data.has_key("id"):
            print "Mysterious UDP data"
        if not self.clients.has_key(str(data["id"])):
            print "Mysterious UDP Data ID",data["id"]
        self.clients[data["id"]].udpAddr = addr
        if self.clients[data["id"]].addr[0] != addr[0]:
            print "Hacking from",addr,"trying to be player",data["id"]
        self.clients[data["id"]].collect_incoming_data(data["content"])
        self.clients[data["id"]].found_terminator()

    def Add5Rooms(self):
        #self.AddTestingGame("Testing area")
        for x in range(5):
            self.AddBasicGame("Friendly pitch "+str(x+1))
    def AddBasicGame(self,name):
        self.gameWorlds[name] = BasicGame(name)
        self.dictOrder.append(name)
    def AddTestingGame(self,name):
        self.gameWorlds[name] = TestingGame(name)
        self.dictOrder.append(name)
    def NextId(self):
        self.id += 1
        return self.id
        if len(self.clients) < self.max_players:
            allowed = True
            reason = ""
        else:
            allowed = False
            reason = "Server full"
        return allowed , reason
    def AllowEntrance(self):
        if len(self.clients) < self.max_players:
            allowed = True
            reason = ""
        else:
            allowed = False
            reason = "Server full"
        return allowed , reason
    def Connected(self , channel , addr):
        print ""
        print "Player connected (",addr,"), the id=",channel.id,"has just been assigned"
        print "Waiting to him to define if he'll play or only request information..."
        self.clients[channel.id] = channel
        channel.ip   = addr[0]
        channel.conn = addr[1]
    def LogicUpdate(self):
        self.Pump()
        for room in self.gameWorlds.keys():
            self.gameWorlds[room].LogicUpdate()
    def CommandThreadDef(self):
        while self.play:
            command = raw_input("Command>")
            self.Command(command)
    def Command(self,com):
        if com == "exit":
            self.play = False
        elif com == "all-players":
            self.ShowAllPlayers()
        else:
            print "command",com," not found"
    def HandlePlayerLost(self,player):
        del self.clients[player.id]
    def ShowAllPlayers(self):
        pass
    def GetBasicInfo(self):
        allow , reason = self.AllowEntrance()
        return {"mode":self.mode,"players":len(self.players.keys()),"max-players":self.max_players,"allow":allow,"reason":reason}
    def GetRoomsData(self):
        rooms = []
        for key in self.dictOrder:
            data = self.gameWorlds[key].GetBasicData()
            rooms.append(data)
        return rooms
    def JoinPlayer(self,player,room_name):
        self.gameWorlds[room_name].JoinPlayer(player)
    def GetPlayers(self):
        return Heads.heads
