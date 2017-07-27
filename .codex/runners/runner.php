<?php

#################################################
## IMPORTANT
## changes out of the 'runner' directorym
## drops to an unprivileged user
$rundir = getenv('RUN_DIRECTORY');
if (!$rundir) {
    exit(1);
}
chdir($rundir);

$uid = getenv('RUN_UID');
$gid = getenv('RUN_GID');
if ($uid && $gid) {
    posix_setgid($gid);
    posix_setegid($gid);

    posix_setuid($uid);
    posix_seteuid($uid);
}

if (in_array(0, array(posix_getuid(), posix_geteuid(), posix_getgid(), posix_getegid()))) {
    exit(5);
}

stream_set_timeout(STDIN, 60*60);

# and now clean out the env
putenv('RUN_DIRECTORY');
putenv('RUN_UID');
putenv('RUN_GID');
# END SETUP
#################################################


# ensure errors are directed to STDOUT
ini_set('display_errors', 'stdout');
ini_set('log_errors', false);

function clean_error_message($string) {
  $regex = '/in '.preg_quote(__FILE__, '/').'\(\d*\) : eval\(\)\'d code /';
  $string = (string)preg_replace($regex, '', $string);
  return $string;
}

function message_for_output($message) {
  return "OUTPUT " . (string)$message . "\r";
}

function send_result($result) {
    echo("RESULT " . json_encode($result) . "\r");
}

function codecademy_ob_callback($buffer) {
  $output = clean_error_message($buffer);
  return message_for_output($output);
}

function codecademy_error_handler($errno, $errstring, $errfile, $errline) {
  echo clean_error_message($errstring) . " (line $errline)";

  // return true to stop processing of errors
  return true;
}

function codecademy_shutdown_handler() {
  $error = error_get_last();
  if ($error['type'] === E_ERROR || $error['type'] === E_COMPILE_ERROR) {
    // fatal error has occured, so lets finish the request and restart
    ob_end_flush();
    send_result(255);
  }
}
register_shutdown_function('codecademy_shutdown_handler');

function runCode($codez) {
    ob_start("codecademy_ob_callback");
    set_error_handler('codecademy_error_handler');

    // error handled by the error handler
    $result = eval('?>' . $codez . '<?php ');

    ob_end_flush();
    send_result($result);

    // Sleep for 300ms, this ensures the respawn event is not handled before
    // the result event in the codex interpreter
    usleep(300000);

    // exit 255 to trigger a restart of the interpreter
    // Because a runner right now is really only good for one
    // Use (the main problem being that functions cannot be re-
    // defined)
    exit(255);
}

function codex_readline() {
    return fgets(STDIN);
}

function getcode() {
    $code = '';
    $spin = true;
    while ($spin) {
        $line = codex_readline();

        if ($line == "\r\n") {
            $spin = false;
        } else {
            $code = $code . $line;
        }
    }
    return str_replace("\\r", "\r", $code);
}

function run() {
    $spin = true;
    while ($spin) {
        $command_line = codex_readline();
        if ($command_line === false) {
            $spin = false;
        } else {
            $command = trim($command_line);
            $code = getcode();
            if ($command == "RUN") {
                runCode($code);
            }
        }
    }
}

run();

?>