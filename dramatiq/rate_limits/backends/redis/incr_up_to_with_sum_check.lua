-- incr_up_to_with_sum_check(
--   keys=[key, *keys]
--   args=[amount, maximum, ttl]
-- )
--
-- Atomically increment `key` by `amount`, unless:
--   - the incremented value is greater than `maximum`, or
--   - the incremented sum of `keys` is greater than `maximum`.

-- split the key list into the first - `key` and the rest - `keys`
local key = KEYS[1]
local keys = {}
for i, k in ipairs(KEYS) do
    if i > 1 then
        keys[i - 1] = KEYS[i]
    end
end

local amount = tonumber(ARGV[1])
local maximum = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

-- check if `key` can be incremented, bail if not
local value = redis.call('GET', key) or 0
if value + amount > maximum then
    return false
end

-- check if sum of `keys` can be incremented, bail if not
local values = redis.call('MGET', unpack(keys))
local sum = 0
for _, v in ipairs(values) do
    if v then
        sum = sum + tonumber(v)
    end
end
if sum + amount > maximum then
    return false
end

-- increment `key` if we got this far
redis.call('SET', key, value + amount, 'PX', ttl)
return true
