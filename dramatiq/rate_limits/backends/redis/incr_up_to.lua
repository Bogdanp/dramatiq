-- incr_up_to(
--   keys=[key]
--   args=[amount, maximum, ttl]
-- )
--
-- Increment `key` by `amount`, unless the resulting value is greater than `maximum`.

local key = KEYS[1]
local amount = tonumber(ARGV[1])
local maximum = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

local value = redis.call('GET', key) or 0
if value + amount > maximum then
    return false
end

redis.call('SET', key, value + amount, 'PX', ttl)
return true
