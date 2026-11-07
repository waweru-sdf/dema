<?php

/*
 * Front door of the website. Every address that is not a real file arrives here (see .htaccess).
 * The Laravel application itself lives OUTSIDE public_html, in the folder "dema-app" next to it,
 * so its code, settings (.env) and uploaded pictures can never be downloaded from the web.
 */

use Illuminate\Http\Request;

define('LARAVEL_START', microtime(true));

$appDir = getenv('DEMA_APP_DIR') ?: dirname(__DIR__) . '/dema-app';
if (!is_file($appDir . '/vendor/autoload.php')) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=UTF-8');
    exit("The website is being set up. Please try again in a few minutes.\n");
}

if (file_exists($maintenance = $appDir . '/storage/framework/maintenance.php')) {
    require $maintenance;
}

require $appDir . '/vendor/autoload.php';

(require_once $appDir . '/bootstrap/app.php')
    ->usePublicPath(__DIR__)
    ->handleRequest(Request::capture());
