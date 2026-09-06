#!/usr/bin/env ruby
# frozen_string_literal: true

# pins.rb — read recipe.yml's `tools:` block (the repo's toolchain pin
# SSOT) and emit KEY=VALUE lines for $GITHUB_ENV. The workflows carry NO
# version or digest literals — every value flows from the recipe.
#
#   ruby tools/pins.rb <tool-platform> [--env]
#
# <tool-platform> is the tebako release asset platform (macos-arm64,
# macos-x86_64, linux-gnu-x86_64, linux-gnu-arm64, linux-musl-x86_64,
# linux-musl-arm64). Unknown platform / missing pin is a named error,
# never a guess (spec 00 §9).
#
# NEVER emit a bare TEBAKO_VERSION: the shim/store grammar uses that name
# for the RUNTIME's tebako line in other repos' tooling; here the tools
# version lives inside the computed ASSET names and the runtime's tebako
# line is RUNTIME_TEBAKO (recipe build.runtime.tebako).

require "yaml"

def die(msg)
  warn "pins.rb: #{msg}"
  exit 64
end

root = File.expand_path("..", __dir__)
recipe = YAML.load_file(File.join(root, "recipe.yml"))
tools = recipe.fetch("tools")
release = tools.fetch("release")
version = release.sub(/\Av/, "")
die "recipe.yml tools.sha256 missing" unless tools["sha256"].is_a?(Hash)

runtime = recipe.fetch("build").fetch("runtime")

pairs = {
  "TEBAKO_RELEASE" => release,
  "PKG_NAME" => recipe.fetch("name"),
  "PKG_VERSION" => recipe.dig("upstream", "version") ||
                   die("recipe.yml upstream.version missing"),
  # The runtime channel (README decision 4): the factory release tag the
  # release channel stages from (the owner's publish decision landed
  # 2026-09-06 — tebako-runtime-python v0.1.0 is live). The pre-publish
  # run-artifacts channel remains selectable by env override in
  # tools/stage_runtime for pre-publish factory proof builds.
  "RUNTIME_CHANNEL" => runtime.fetch("channel"),
  "RUNTIME_RELEASE" => runtime["release"].to_s,
  "RUNTIME_FACTORY_RUN" => runtime["factory_run"].to_s,
  "RUNTIME_PYTHON" => runtime.fetch("version"),
  "RUNTIME_TEBAKO" => runtime.fetch("tebako"),
}

# triplet -> the tebako release-asset platform (spec 03 §3; identical to
# the factory's host_id on the POSIX six — tools/build's ASSET_PLATFORM).
TOOL_PLATFORM = {
  "x86_64-linux-gnu" => "linux-gnu-x86_64",
  "aarch64-linux-gnu" => "linux-gnu-arm64",
  "x86_64-linux-musl" => "linux-musl-x86_64",
  "aarch64-linux-musl" => "linux-musl-arm64",
  "x86_64-macos" => "macos-x86_64",
  "aarch64-macos" => "macos-arm64",
}.freeze

if ARGV.include?("--matrix")
  # The CI leg matrix from the recipe's platforms + ci blocks (the SSOT —
  # the workflow carries NO host/container literals). Emits the build
  # job's matrix JSON: triplet, host runner, tool asset platform, and the
  # container image (musl legs only — "null" for host-native legs).
  require "json"
  ci = recipe.fetch("ci")
  hosts = ci.fetch("hosts")
  containers = ci["containers"] || {}
  include = recipe.fetch("platforms").map do |triplet|
    host = hosts[triplet] or die "recipe.yml ci.hosts has no host for #{triplet}"
    tp = TOOL_PLATFORM[triplet] or die "pins.rb: unknown triplet #{triplet}"
    {
      triplet: triplet,
      host: host,
      tool_platform: tp,
      container: containers[triplet] || "",
    }
  end
  puts JSON.generate({ include: include })
  exit 0
end

if ARGV.include?("--payload-args")
  # The release job's tebako publish --payload arguments, derived from the
  # recipe platforms (no triplet/artifact literals in the workflow):
  #   --payload <triplet>=out/<triplet>/<name>-<version>-<asset-platform>.tfs ...
  name = recipe.fetch("name")
  ver = recipe.dig("upstream", "version") or die "recipe.yml upstream.version missing"
  puts recipe.fetch("platforms").map { |t|
    tp = TOOL_PLATFORM[t] or die "pins.rb: unknown triplet #{t}"
    "--payload #{t}=out/#{t}/#{name}-#{ver}-#{tp}.tfs"
  }.join(" ")
  exit 0
end

platform = ARGV[0] or die "usage: pins.rb <tool-platform> [--env]"
{ "tebako" => "TEBAKO", "tfs" => "TFS", "tebako-pkg" => "TEBAKO_PKG",
  "tebako-shim" => "SHIM" }.each do |tool, key|
  sha = tools.dig("sha256", tool, platform) or
    die "recipe.yml: no tools.sha256.#{tool}.#{platform} pin"
  exe = ""
  pairs["#{key}_ASSET"] = "#{tool}-#{version}-#{platform}#{exe}"
  pairs["#{key}_SHA256"] = sha
end

if ARGV.include?("--env")
  pairs.each { |k, v| puts "#{k}=#{v}" }
else
  pairs.each { |k, v| puts "export #{k}=#{v}" }
end
