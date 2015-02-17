__author__ = 'newtonis'

ping_server = 0
ping_client = 0
irregular_ping = 0 #%

local_host = "localhost"
dylan_server_host = "192.168.1.45"
newtonis_server_host = "192.168.1.59"

current_host = dylan_server_host #currently is not being used as there is a raw_input

threshold = 0.001 #correction in the client, if a target position has less than threshold distance, it is corrected
interpolation_constant = 0.30 #smooth client movement speed
match_duration = 3 #the duration of the match in minutes