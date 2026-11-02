-- decr_down_to(
--   keys=[key]
--   args=[amount, minimum, ttl]
-- )
--
-- Decrement `key` by `amount`, unless the resulting value is less than `minimum`.

local key = KEYS[1]
local amount = tonumber(ARGV[1])
local minimum = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

local value = redis.call('GET', key) or 0
if value - amount < minimum then
    return false
end

redis.call('SET', key, value - amount, 'PX', ttl)
return true
