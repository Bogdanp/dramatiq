-- This file is a part of Dramatiq.
--
-- Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
--
-- Dramatiq is free software; you can redistribute it and/or modify it
-- under the terms of the GNU Lesser General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or (at
-- your option) any later version.
--
-- Dramatiq is distributed in the hope that it will be useful, but WITHOUT
-- ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
-- FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
-- License for more details.
--
-- You should have received a copy of the GNU Lesser General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.

-- nack(args=[queue_name, xqueue_name, message_id, timestamp])
-- This function removes a message from a queue's acks set and then
-- moves it to a dead-letter queue.
local queue_name = ARGV[1]
local xqueue_name = ARGV[2]
local message_id = ARGV[3]
local timestamp = ARGV[4]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"
local xqueue_messages = xqueue_name .. ".msgs"

-- unack the message
redis.call("zrem", queue_acks, message_id)

-- then pop it off the messages hash and move it onto the DLQ
local message = redis.call("hget", queue_messages, message_id)
if message ~= nil then
   redis.call("hdel", queue_messages, message_id)
   redis.call("hset", xqueue_messages, message_id, message)
   redis.call("zadd", xqueue_name, timestamp, message_id)
end
