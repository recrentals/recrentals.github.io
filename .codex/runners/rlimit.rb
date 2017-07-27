## This is a script to apply pre-configured resource limits
## then exec another script.
##
## ruby rlimit.rb <config_slug> -- args for other command
##
## config slug is the slug that will be used to look up rlimit configs
## -- separates the other arguments, which are not un through a shell, but
##    a exec system call. So full paths and such necessary.


## Uses following exit codes (no control over execed-process codes though)
## 2 - bad arguments
## 3 - no config for given slug
## 4 - config missing resource limit specification
## 5 - Effective user / group still root (will come from child)
EXIT_BAD_ARGS = 2
EXIT_MISSING_CONFIG = 3
EXIT_BAD_CONFIG = 4
EXIT_SUPERUSER = 5

## Rlimit config information.
MB =  1024*1024
LIMITS_CONFIG_BY_COMMAND = {
  'python' => {
    RLIMIT_CORE: [0, 0],
    RLIMIT_NPROC: [1, 4],
    RLIMIT_NOFILE: [25, 30],
    RLIMIT_CPU: [60, 70],
    RLIMIT_DATA: [8*MB, 10*MB],
    RLIMIT_AS: [128*MB, 128*MB],
    RLIMIT_FSIZE: [1*MB, 1.5*MB]
  },
  'python_server' => {
    RLIMIT_CORE: [0, 0],
    RLIMIT_NPROC: [4, 4],
    RLIMIT_NOFILE: [25, 30],
    RLIMIT_CPU: [60, 70],
    RLIMIT_DATA: [8*MB, 10*MB],
    RLIMIT_AS: [128*MB, 128*MB],
    RLIMIT_FSIZE: [1*MB, 1.5*MB]
  },
  'ruby' => {
    RLIMIT_CORE: [0, 0],
    RLIMIT_NPROC: [5, 5],
    RLIMIT_NOFILE: [25, 30],
    RLIMIT_CPU: [60, 70],
    RLIMIT_DATA: [8*MB, 10*MB],
    RLIMIT_AS: [128*MB, 128*MB],
    RLIMIT_FSIZE: [1*MB, 1.5*MB]
  },
  'php' => {
    RLIMIT_CORE: [0, 0],
    RLIMIT_NPROC: [5, 5],
    RLIMIT_NOFILE: [25, 30],
    RLIMIT_CPU: [60, 70],
    RLIMIT_DATA: [8*MB, 10*MB],
    RLIMIT_AS: [128*MB, 128*MB],
    RLIMIT_FSIZE: [1*MB, 1.5*MB]
  }
}

## Arg parsing
# first separate the args by --
sep_index = ARGV.index '--'
exit(EXIT_BAD_ARGS) if sep_index.nil?

leading_args = ARGV.slice(0, sep_index)

cmd_args = ARGV.slice(sep_index+1, ARGV.size - 1 - sep_index)
exit(EXIT_BAD_ARGS) if cmd_args.empty?

config_slug = leading_args[0]
exit(EXIT_BAD_ARGS) if config_slug.nil?

# Set a bunch of system limits for the process. Comments below include the
# signal that is sent when the soft limit is reached, if applicable. SIGKILL
# is always sent if the hard limit is reached. See getrlimit(2).
limit_config = LIMITS_CONFIG_BY_COMMAND[config_slug]
exit(EXIT_MISSING_CONFIG) unless limit_config

[
  :RLIMIT_CORE,   # disable core dumps
  :RLIMIT_NPROC,  # EAGAIN  - num processes
  :RLIMIT_NOFILE, # EMFILE  - file descriptors
  :RLIMIT_CPU,    # SIGXCPU - CPU time
  :RLIMIT_DATA,   # ENOMEM  - data (heap)
  :RLIMIT_AS,     # ENOMEM     - data (virtual memory)
  :RLIMIT_FSIZE   # SIGXFSZ - file size
].each do |limit_type|
  limit = limit_config[limit_type]
  exit(EXIT_BAD_CONFIG) if limit.nil? || limit.empty?

  Process.setrlimit(Process.const_get(limit_type), *limit)
end

begin
  ## Strip supplementary groups from the process before we drop privilege
  Process.groups = []
rescue Errno::EPERM
  # then we must be in dev mode
end

# ok we here!
exec(*cmd_args)