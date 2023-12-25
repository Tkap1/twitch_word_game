
import os
import socket
import threading
import time
import random

g_twitch = None
g_target_channel = "tkap1"
g_msgs = []
g_read_index = 0

def main():
	global g_twitch
	twitch_token = os.environ["twitch_token"]
	twitch_client_id = os.environ["twitch_client_id"]

	threading.Thread(target=do_game).start()

	while True:
		g_twitch = socket.create_connection(("irc.chat.twitch.tv", 6667))
		send(g_twitch, "PASS oauth:%s" % twitch_token)
		send(g_twitch, "NICK %s" % g_target_channel)
		send(g_twitch, "CAP REQ :twitch.tv/commands twitch.tv/tags")
		try:
			print(receive(g_twitch))
			break

		except ConnectionResetError:
			print("Failed to connect to twitch, retrying...")
			g_twitch.close()

	send(g_twitch, "JOIN #%s" % g_target_channel)
	while True:
		data = receive(g_twitch)
		if not data: break
		data = data.decode()
		data = data.splitlines()[0]

		if "PRIVMSG" in data:
			splits = data.split(";")
			parsed = {}
			for s in splits:
				if "user-type" in s: break;
				s2 = s.split("=")
				assert len(s2) == 2
				parsed[s2[0]] = s2[1]

			msg = data[data.index("PRIVMSG") + len(f"PRIVMSG #{g_target_channel} :"):]
			g_msgs.append([parsed["display-name"], msg])

		elif "PING" in data:
			send(g_twitch, data.replace("PING", "PONG"))

	g_twitch.close()


def do_game():
	global g_read_index

	time.sleep(1)

	while g_twitch == None:
		continue

	with open("nouns.txt", "r") as f:
		words = f.read().split("\n")
	words = [w for w in words if len(w) > 0]

	restart_game = True
	chosen = 0
	curr_round = 0
	round_start_time = 0
	players = {}

	while True:
		if restart_game:
			restart_game = False
			curr_round = 0
			advance_round = True
			players = {}

		if advance_round:
			advance_round = False
			curr_round += 1

			if curr_round >= 8:
				sorted_players = dict(sorted(players.items(), key=lambda item: item[1], reverse=True))
				if len(sorted_players) > 1 and list(sorted_players.values())[0] == list(sorted_players.values())[1]:
					send_chat_msg(g_twitch, f"There was a tie! Let's do another round!")

				else:
					send_chat_msg(g_twitch, f"{list(sorted_players.keys())[0]} wins!")
					for key in list(sorted_players.keys())[:5]:
						value = sorted_players[key]
						send_chat_msg(g_twitch, f"{key}: {value}")
						time.sleep(1)
					input("Press ENTER...")
					restart_game = True
					continue

			round_start_time = time.time()
			chosen = random.randrange(0, len(words))
			print(f"The word is: {words[chosen]}")
			send_chat_msg(g_twitch, f"Round {curr_round} started!")

		if time.time() - round_start_time >= 60:
			send_chat_msg(g_twitch, f"Nobody got it! The word was: {words[chosen]}")
			curr_round -= 1
			advance_round = True

		while g_read_index < len(g_msgs):
			msg = g_msgs[g_read_index]
			g_read_index += 1
			if msg[1].lower() == words[chosen].lower():
				score = players.setdefault(msg[0], 0)
				players[msg[0]] = score + 1
				advance_round = True
				send_chat_msg(g_twitch, f"{msg[0]} got it! The word was: {words[chosen]}")
				break

		time.sleep(0.01)

def send_chat_msg(twitch, to_send):
	send(twitch, f"PRIVMSG #{g_target_channel} :{to_send}")


def send(twitch, to_send):
	twitch.send(bytes(to_send + "\n", encoding="utf-8"))

def receive(twitch):
	data = twitch.recv(8192)
	return data



if __name__ == "__main__":
	main()