// Boilerplate from : https://medium.com/davao-js/tutorial-creating-a-simple-discord-bot-9465a2764dc0

var MarkovProvider = require('./sqlite-backend.js')

var Discord = require('discord.io');
var auth = require('./discord-auth.json');

const markov = {};

// Initialize Discord Bot
var bot = new Discord.Client({
   token: auth.token,
   autorun: true,
});

bot.on('message', function (user, userID, channelID, message, evt) {
	if (userID === bot.id) return;
	
	const userHandle = `<@${bot.id}>`;
	const maxReplyWords = (message.includes(userHandle)) ? 25 : 0;
	
	if (!bot.channels[channelID]) return; // TODO : Maybe handle DMChannels?

	let server_id = bot.channels[channelID].guild_id;
	let server_namespace = `discord_${server_id}`;
	console.log(`(${server_id}) => "${message}"`);
	
	if (markov[server_namespace] === undefined) {
		console.info(`Opening DB for ${server_namespace}`);
		markov[server_namespace] = new MarkovProvider(server_namespace);
	}

	markov[server_namespace].record_and_generate(message, maxReplyWords).then((markovReply) => {
		if (!markovReply || markovReply.length === 0) return null
		return markovReply.join(' ');
	})
	.catch(err => console.error('Error executing query', err.stack))
	.then((msg) => {
		if (!msg) return;
		console.log(`(${server_id}) <= "${msg}"`);
		
		bot.sendMessage({
				to: channelID,
				message: msg,
		});
	});
});

bot.on('ready', function (evt) {
    console.info(`Logged in as: ${bot.username} - (${bot.id})`);
});

bot.on('disconnect', function(errMsg, code) {
	console.error(`Disconnected : ${errMsg} (${code})`);
});
