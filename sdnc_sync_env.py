
import random
import time
import networkx as nx
import numpy as np
import topologies as tp
from networkx import json_graph

WEIGHTS_CHANGE_TIME = 1
SYNC_TIME = 1
#arrival_rates = [32, 64, 18, 51, 32, 27, 27, 56, 74, 30, 67, 61, 52, 78, 53, 80, 80, 14, 22, 34, 15, 38, 19, 73, 57, 68, 70, 79, 70, 44, 36, 34, 77]
arrival_rates = [32, 64, 18, 51, 34, 56, 94, 93, 94, 90, 97, 91, 92, 98, 53, 80, 80, 14, 22, 34, 15, 38, 19, 73, 57, 68, 70, 79, 70, 44, 36, 34, 77]
action_space = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
#each of the four variables in the state representation can take 11 values (0-10)
max_tslots = 60
n_state_space = max_tslots**4

def to_index(state):
    '''
    returns state index from a given state
    '''

    index = state[0]*max_tslots*max_tslots*max_tslots + state[1]*max_tslots*max_tslots + state[2]*max_tslots + state[3]

    return int(index)


def get_state(controller):
    #This function returns the current state of the environment
    #i.e., the desynchronization time slots of controller A with respect to the others 
    #print("****get_state")

    return to_index(controller.desync_list)


def get_reward(controller,real_net):
    #This function calculates the reward "r" after taking an action "a" under state "s"
    #it is evaluated by calculating the paths for a set of src-dst and computing their path costs
    #path cost is the sum of the weights in the links composing the path
    #print("get_reward")
    path_cost_list = [] 
    difference = []
    G = nx.node_link_graph(controller.network.topology.graph) 
    #print(json_graph.node_link_data(G)["links"])
    real_links = real_net.topology.graph["links"]
    #print("real_links",real_links)

    for src in range(4):
        for dst in range(4,23):
            path = nx.shortest_path(G, source = src, target = dst, weight="weight")#con la vista del controlador A
            #print(path, end="- ")
            #path_cost_A = nx.shortest_path_length(G, source =src, target= dst,weight="weight")#costo visto por controller A
            
            path_cost_A = 0 #costo visto por controller A
            for i in range(len(path)-1):
                #links.append([path[i],path[i+1]])
                for l in controller.network.topology.graph["links"]:
                    if (l["source"] == path[i] and l["target"] == path[i+1]) or (l["source"] == path[i+1] and l["target"] == path[i]):
                        path_cost_A += l["weight"]
            #print("path_cost_A:",path_cost_A, end="- ")
                                   
            #calculate real path cost
            path_cost=0 
            for i in range(len(path)-1):
                #links.append([path[i],path[i+1]])
                for l in real_links:
                    if (l["source"] == path[i] and l["target"] == path[i+1]) or (l["source"] == path[i+1] and l["target"] == path[i]):
                        path_cost += l["weight"]
            
            
            #print("real path cost:",path_cost)            
            path_cost_list.append(path_cost)
            difference.append(abs(path_cost-path_cost_A))
            #print("dif:",abs(path_cost-path_cost_A))
    #print(np.mean(path_cost_list))
    #return np.mean(path_cost_list)
    return -np.mean(difference), np.mean(path_cost_list)
    
# def get_new_weights():
#     #This function generates new weights for the links according to a uniform distribution 
#     new_weights = []
#     for link_index in range(33):
#         new_weight = random.randint(0,100) 
#         print(link_index,new_weight)
#         new_weights.append(new_weight)

#     return new_weights

def get_new_weights():
    #This function generates new weights for the links according to a poisson distribution 
    new_weights = []

    for i in arrival_rates:
        new_weights.append(np.random.poisson(lam=i,size=1))    

    return new_weights



def update_weights(controllers, real_net, new_weights = get_new_weights()):     

    #update weights in "real network"
    real_links = real_net.topology.graph["links"]
    for i in range(len(real_links)):
        real_links[i]["weight"] = new_weights[i]

    #This function receives a list of controllers and a list of new weights
    #to update the link weights in their corresponding domains
    #controllers have a partial view of the network (real_net) only
    for j in range(len(controllers)):
        links_list = controllers[j].network.topology.graph["links"]
        for i in range(len(links_list)):
            
            if (links_list[i]["domain"] == controllers[j].domain) or (links_list[i]["domain"] == (str(controllers[j].domain)+str(controllers[j+1].domain if j+1<len(controllers) else ""))):
                #print("controlador:",j,"i",i)
                links_list[i]["weight"] = new_weights[i]


        
    
def sync(controller_X,controller_Y): 
    #This function receives two controllers (X and Y) to update X's network view with Y's domain network view
    
    links_X = controller_X.network.topology.graph["links"]
    links_Y = controller_Y.network.topology.graph["links"]
    

    for i in range(len(links_Y)):
        if links_Y[i]["domain"] == controller_Y.domain or links_Y[i]["domain"] == controller_Y.interdomain:#  or links_Y[i]["domain"] == (str(controller_Y.domain)+str(domains[pos+1] if pos+1<len(domains) else "")):
            #print("*i",i)
            links_X[i]["weight"] = links_Y[i]["weight"]

    #the count of desync time slots is updated according to the X and Y sincronization
    #0:B, 1:C. 2:D, 3:E
    pos = {"B":0,"C":1,"D":2,"E":3} 
    controller_X.desync_list[pos[controller_Y.domain]] = 0   


class Network(object):
    def __init__(self, topology):
        self.topology = topology


class Controller(object):
    def __init__(self, domain,interdomain=""):
        self.domain = domain
        self.interdomain = interdomain
        self.network = Network(tp.get_topo("multidomain_topo"))
        self.desync_list = [0,0,0,0]


class Evento:
    def __init__(self, tipo, inicio, extra, function):
        self.tipo = tipo
        self.inicio = inicio
        self.extra = extra
        self.function = function

    def __str__(self):
        return "("+self.tipo+","+str(self.inicio)+","+str(self.extra)+")"


class Simulation:
    def __init__(self):
        self.eventos = []
        self.total_events = 0
        self.horario = 0
        self.run_till = -1
        self.network = Network(tp.get_topo("multidomain_topo"))
        self.controllers = [Controller("A","AB"),Controller("B","BC"),Controller("C","CD"),Controller("D","DE"),Controller("E")]
        self.new_weights = []
        #metrics:
        self.APC = 0 #average path cost
        self.xtime = 0                    

    def set_run_till(self, t):
        self.run_till = t

    def create_event(self, tipo, inicio, extra=None, f=None):
        if inicio<self.horario:
            print("***false")
            return False
        # else:     
        e = Evento(tipo, inicio, extra, f)
        return e

    def binary_search (self, arr, l, r, x):
        if r >= l:       
            mid = int(l + (r - l)/2)
            if arr[mid].inicio == x: 
                return mid
            elif arr[mid].inicio > x: 
                return self.binary_search(arr, l, mid-1, x) 
            else: 
                return self.binary_search(arr, mid+1, r, x)   
        else:             
           return l

    def add_event(self, evt):        
        request = {}
        #encontrar indice y adicionar event en esa posicion
        index = self.binary_search(self.eventos, 0, len(self.eventos)-1, evt.inicio)
        self.eventos = self.eventos[:index] + [evt] + self.eventos[index:] 

    def print_eventos(self):
        print("HORARIO: ",self.horario,"\nTotal Eventos:",len(self.eventos))
        for i in range(len(self.eventos)): 
            print(self.eventos[i].tipo,self.eventos[i].inicio, end=" > ")
        print("\n")

    #def get_proximo_evento(self):
    #    if len(self.eventos)==0:
    #        return None
    #    else:
    #        p = self.eventos.pop(0)
    #        self.horario = p.inicio
    #        return p

    def get_proximo_evento(self):
        if len(self.eventos)==0:
            return None
        else:
            p = self.eventos[0]
            #self.horario = p.inicio
            return p
    

    # def run(self):

    #     next_event = self.get_proximo_evento()
    #     #while self.horario<self.run_till:
    #     while next_event.tipo != "sync":
    #         #self.print_eventos()    
        
    #         if next_event==None:
    #             return

    #         next_event.function(self,next_event)
    #         next_event = self.get_proximo_evento()

    #     state = get_state(self.controllers[0])    
    #     return state    

    def run(self):
        while self.horario<self.run_till:        
            next_event = self.get_proximo_evento()     
            if next_event==None:
                return

            if next_event.tipo != "sync":
                self.horario = next_event.inicio
                self.eventos.pop(0)
                next_event.function(self,next_event)

            else:
                update_weights(self.controllers,self.network)
                #the count of desync time slots is carried out
                for j in range(len(self.controllers)):
                    for i in range(len(self.controllers[j].desync_list)):
                        if self.controllers[j].desync_list[i] < max_tslots-1:
                            self.controllers[j].desync_list[i] += 1
                return get_state(self.controllers[0]) 

               

    def step(self,action):
        #print("stepppp")
        if self.eventos[0].tipo=="sync":
            #print("#evento sync")
        
            self.eventos[0].function(self,self.eventos[0],action)
            self.horario = self.eventos[0].inicio
            self.eventos.pop(0)

        while self.horario<self.run_till:
            next_event = self.get_proximo_evento()
            #if next_event==None:
            #     return
            if next_event.tipo != "sync":
                self.horario = next_event.inicio
                self.eventos.pop(0)
                next_event.function(self,next_event)

            else:
                update_weights(self.controllers,self.network)
                #the count of desync time slots is carried out
                for j in range(len(self.controllers)):
                    for i in range(len(self.controllers[j].desync_list)):
                        if self.controllers[j].desync_list[i] < max_tslots-1:
                            self.controllers[j].desync_list[i] += 1
                return get_state(self.controllers[0])




def get_src_dst():
    #returns a list of lists, each list containing a src-dst pair with its arrival rate, ex: [[src,dst,arrival_rate],[],..[]]
    src_dst_list = []
    for src in range(4):
        for j in range(10):
            dst = random.randint(4,23)
            arrival_rate = random.randint(1,6)
            src_dst_list.append([src,dst,arrival_rate])
    return src_dst_list

def func_update_weights(sim, evt): #modify weights in links according to a distribution
    
    #print("change_weights function")
    update_weights(sim.controllers,sim.network)
    sim.add_event(sim.create_event(tipo="weights_change",inicio=sim.horario+WEIGHTS_CHANGE_TIME, extra={}, f=func_update_weights))


def func_synchronize(sim, evt, action):
    #It is time for syncronization event, controller A will decide which of the other controllers to syncronize with     
    #print("synchronize function")
    a = action_space[action]
    index=a.index(1)
    
    sync(sim.controllers[0],sim.controllers[index+1])      
    
    evt = sim.create_event(tipo="sync",inicio=sim.horario+SYNC_TIME, extra={}, f=func_synchronize)    
    sim.add_event(evt)



def init_sim(sim):
    #evt = sim.create_event(tipo="weights_change",inicio=sim.horario+WEIGHTS_CHANGE_TIME,extra={},f=func_update_weights)
    #sim.add_event(evt)

    evt = sim.create_event(tipo="sync",inicio=sim.horario+SYNC_TIME,extra={},f=func_synchronize)
    sim.add_event(evt)

sim = None

def reset():
    global sim 
    sim = None
    sim = Simulation()
    sim.set_run_till(max_tslots)
    init_sim(sim) 
    first_state = sim.run()
    return first_state

def step(action):
    global sim
    next_state = sim.step(action)
    reward, APC = get_reward(sim.controllers[0],sim.network)
    done = True if (sim.horario>=sim.run_till) else False # or (10 in sim.controllers[0].desync_list) else False
    #print("hora:",sim.horario)
    
    info = {"APC":APC}
    return next_state, reward, done, info




# sim = Simulation()
# sim.set_run_till(60)
# print(sim.network.topology.graph["links"])
# print()
# print(sim.controllers[0].network.topology.graph["links"])
# print("**",sim.network.topology.graph["links"] == sim.controllers[0].network.topology.graph["links"])
# update_weights(sim.controllers,sim.network)
# print(sim.network.topology.graph["links"])
# print()
# print(sim.controllers[0].network.topology.graph["links"])
# print("**",sim.network.topology.graph["links"] == sim.controllers[0].network.topology.graph["links"])
# sync(sim.controllers[0],sim.controllers[1])
# print(sim.network.topology.graph["links"])
# print()
# print(sim.controllers[0].network.topology.graph["links"])
# print("**",sim.network.topology.graph["links"] == sim.controllers[0].network.topology.graph["links"])max_tslots
