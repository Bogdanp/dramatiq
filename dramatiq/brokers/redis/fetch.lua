-- fetch(args=[queue_name, prefetch, timeout])
local queue_name = ARGV[1]
local prefetch = ARGV[2]
local timeout = ARGV[3]  -- ignored

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

local message_ids = {}
local message_id
for i=1,prefetch do
   message_id = redis.call("rpoplpush", queue_name, queue_acks)
   if not message_id then
      break
   end

   message_ids[i] = message_id
end

if next(message_ids) == nil then
   return {}
else
   return redis.call("hmget", queue_messages, unpack(message_ids))
end
