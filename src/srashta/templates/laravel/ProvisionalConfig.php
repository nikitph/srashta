<?php
namespace App\Support;

use RuntimeException;

/** Application code reads project defaults through this boundary. */
final class ProvisionalConfig
{
    public static function read(string $key, bool $acknowledgeProvisional = false): mixed
    {
        foreach (config('srashta.blocked_keys', []) as $blocked) {
            if ($key === $blocked || str_starts_with($key, $blocked.'.') || str_starts_with($blocked, $key.'.')) {
                if (! $acknowledgeProvisional || ! app()->environment(['local', 'testing'])) {
                    throw new RuntimeException('Unanswered configuration blocker: '.$blocked);
                }
            }
        }
        return config('srashta.values.'.$key);
    }
}
