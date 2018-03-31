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

-- fetch(args=[queue_name, prefetch, timestamp])
-- This function fetches up to $prefetch number of messages for a
-- given queue.  All fetched messages are moved to the ack set.  The
-- timestamp is used to "score" each ack such that an external watcher
-- can efficiently move messages unacked some time prior to when it
-- runs back to their respective queues.
local queue_name = ARGV[1]
local prefetch = ARGV[2]
local timestamp = ARGV[3]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

local message_ids = {}
local message_id
for i=1,prefetch do
   message_id = redis.call("lpop", queue_name)
   if not message_id then
      break
   end

   message_ids[i] = message_id
   redis.call("zadd", queue_acks, timestamp, message_id)
end

if next(message_ids) == nil then
   return {}
else
   return redis.call("hmget", queue_messages, unpack(message_ids))
end
