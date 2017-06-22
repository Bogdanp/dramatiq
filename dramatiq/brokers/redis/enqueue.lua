-- enqueue(args=[queue_name, message_id, message_data])
-- This function stores a message in Redis and appends its id to a list.
--
-- ${queue_name} is a Redis list of message ids [message_1, message_2, message_3]
-- ${queue_name}.msgs is a hash of message ids to message payloads
-- ${queue_name}.acks is a zset of message ids scored by the timestamp
-- each message was pulled off the queue.
local queue_name = ARGV[1]
local message_id = ARGV[2]
local message_data = ARGV[3]

local queue_messages = queue_name .. ".msgs"

redis.call("hset", queue_messages, message_id, message_data)
redis.call("rpush", queue_name, message_id)
