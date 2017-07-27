require 'delegate'
require 'stringio'
require 'json'

##################################################

$stdin.sync  = true
$stdout.sync = true
$stderr.sync = true

##################################################
## IMPORTANT
## changes out of the 'runner' directory
## drops to unprivileged user

Dir.chdir(ENV.fetch('RUN_DIRECTORY'))

uid = ENV['RUN_UID']
gid = ENV['RUN_GID']
if uid && gid
  uid, gid = uid.to_i, gid.to_i
  Process::GID.change_privilege(gid)
  Process::UID.change_privilege(uid)

  if [Process.uid, Process.euid, Process.gid, Process.egid].include?(0)
    exit(5) # do not allow process to run as root.
  end
end

# delete env vars
ENV.delete 'RUN_DIRECTORY'
ENV.delete 'RUN_UID'
ENV.delete 'RUN_GID'

## END SETUP
##################################################

# Constants that are substituted by the network proxy. Defined because
# strings that look like constants are confusing.
ACCOUNT_SID = "ACCOUNT_SID"
API_KEY     = "API_KEY"
AUTH_TOKEN  = "AUTH_TOKEN"
PIN         = "PIN"

HARNESS = <<-STR
  lambda {|code, result, exception, prints|
    %s
  }.call(@__code, @__result, @__exception, $stdout.buffer.split("\n"))
STR

class MyStdout < SimpleDelegator
  def initialize(*args)
    super
    @_buffer = StringIO.new
  end
  def write(str)
    @_buffer.write(str)
    super("OUTPUT #{str}\r")
  end
  def puts(str)
    write(str.to_s+"\n")
  end
  def buffer
    @_buffer.string
  end
  def clear
    @_buffer = StringIO.new
  end
end
$__stdout = $stdout
STDOUT = $stdout = MyStdout.new(Object.send(:remove_const, :STDOUT))

class Context
  def initialize
    @__binding = binding
  end

  def gets(*args)
    $__stdout.print "STDIN\r"
    $<.gets(*args)
  end

  ### HACKS to make API gems play nice ###
  def require(*args)
    super
    case args
    when ["stripe"]
      # so we don't have to shell out to uname
      ::Stripe.class_variable_set(:@@uname, 'Linux Codecademy codex-adapter x86_64 GNU/Linux')

      # gem hard-codes their own bundled ca file, which we need to override
      ::Stripe.class_variable_set(:@@ssl_bundle_path, '/etc/ssl/certs/ca-certificates.crt')
    when ["twilio-ruby"]
      Twilio::REST::Client::DEFAULTS[:ssl_ca_file] = '/etc/ssl/certs/ca-certificates.crt'
    end
  end
  ### END ###

  def __run(codez)
    $stdout.clear
    @__exception = nil
    @__result = nil
    @__code = codez

    begin
      @__result = eval(codez, @__binding, '(ruby)', 0)
      $__stdout.print "RESULT #{@__result.inspect}\r"
    rescue Exception => e
      @__exception = e
      warn e
    end
  end

  def __test(codez)
    begin
      rv = eval(HARNESS % codez, @__binding, '(test)', -1)
    rescue Exception => e
      warn e
    end
    $__stdout.print "RESULT #{rv.inspect}\r"
  end

  def __sct_result(ret)
    $__stdout.print "SCT #{JSON.dump(ret)}\r"
  end

  def __sct(codez)
    ret = {}
    begin
      rv = eval(HARNESS % codez, @__binding, '(test)', -1)
    rescue Exception =>e
      ret[:error] = e.to_s
      __sct_result ret
      return
    end

    if rv == true
      ret[:pass] = true
    else
      ret[:pass] = false
      if rv.is_a? String
        ret[:hint] = rv
      else
        ret[:hint] = nil
      end
    end

    __sct_result ret
  end

  def inspect
    "#<#{self.class}:0x#{object_id.to_s(16)}>"
  end
end

@context = Context.new
while command = STDIN.gets
  command.chomp!

  code = ''
  loop do
    line = STDIN.gets
    break if line == "\r\n"
    code << line if line
  end
  code.gsub!("\\r","\r")

  case command
  when 'RUN'
    @context.__run(code)
  when 'TEST'
    @context.__test(code)
  when 'SCT'
    @context.__sct(code)
  end
end
