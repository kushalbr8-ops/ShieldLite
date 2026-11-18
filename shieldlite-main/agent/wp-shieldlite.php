<?php
/*
Plugin Name: ShieldLite Event Sender
Description: Sends page hits and login attempts to ShieldLite backend.
Version: 0.1
Author: ShieldLite
*/

if (!defined('ABSPATH')) exit;

class ShieldLite_WP {
    private $endpoint = 'http://YOUR_SERVER_IP:8000/event';
    private $apikey = 'PASTE_SHIELD_API_KEY_HERE';

    public function __construct() {
        add_action('wp_head', array($this, 'send_pageview'));
        add_action('wp_login_failed', array($this, 'on_login_failed'), 10, 1);
    }

    public function send_pageview() {
        $this->post_event(array(
            'ip' => null,
            'payload' => 'page_load: ' . $_SERVER['REQUEST_URI'],
            'endpoint' => $_SERVER['REQUEST_URI']
        ));
    }

    public function on_login_failed($username) {
        $this->post_event(array(
            'ip' => null,
            'payload' => 'login_failed',
            'endpoint' => '/wp-login.php'
        ));
    }

    private function post_event($data) {
        $args = array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-API-KEY' => $this->apikey
            ),
            'body' => wp_json_encode($data),
            'timeout' => 3,
        );
        wp_remote_post($this->endpoint, $args);
    }
}

new ShieldLite_WP();