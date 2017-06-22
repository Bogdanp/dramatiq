-- ack(args=[queue_name, message_id])
-- This function removes a message from Redis and then pops off its id
-- from its queue's acks set.
local queue_name = ARGV[1]
local message_id = ARGV[2]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

-- NOTE: Assumes retried messages receive a new, globally-unique, id.
redis.call("hdel", queue_messages, message_id)
redis.call("zrem", queue_acks, message_id)
