#!/usr/bin/env perl
# Restore source character pixels using the generated extraction as a mask guide.
use strict;
use warnings;
use FindBin qw($Bin);
use File::Temp qw(tempdir);

my $layers = "$Bin/layers";
my $output_override;
if (@ARGV && $ARGV[0] eq '--output' && @ARGV == 2) {
    $output_override = $ARGV[1];
    @ARGV = ();
}
my $mask_only = @ARGV && $ARGV[0] eq '--mask-only';
die "Usage: $0 [--output wallpaper | --mask-only source output-mask]\n" if @ARGV
    && (!$mask_only || @ARGV != 3);
my $source = $mask_only ? $ARGV[1] : "$Bin/serena_fennekin_original.jpg";
my $before = "$layers/sunset_before_character_restore.png";
my $guide = "$layers/character_extraction_guide.png";
my $plate = "$layers/sunset_background_plate.png";
my $output = $output_override // "$Bin/../../assets/wallpapers/serena_fennekin_wallpaper_grass_fixed.png";
my $tmp = tempdir('serena-restore-XXXXXX', TMPDIR => 1, CLEANUP => 1);
my $mask_output = $mask_only ? $ARGV[2] : "$tmp/original_mask.png";

sub run {
    system(@_) == 0 or die "Command failed: @_\n";
}
sub read_bytes {
    open my $fh, '<:raw', $_[0] or die "$!: $_[0]";
    local $/;
    return <$fh>;
}
sub dimensions {
    open my $fh, '-|', 'magick', 'identify', '-format', '%w %h', $_[0]
        or die "Cannot identify $_[0]";
    local $/;
    my $result = <$fh>;
    close $fh or die "Image identification failed";
    return split /\s+/, $result;
}

my ($w, $h) = dimensions($source);
my ($out_w, $out_h) = dimensions($before);
my $size = $w * $h;
run('magick', $guide, '-alpha', 'extract', '-resize', "${w}x${h}!",
    '-threshold', '50%', '-morphology', 'Close', 'Disk:1', "$tmp/guide.png");
run('magick', "$tmp/guide.png", '-morphology', 'Erode', 'Disk:14',
    '-depth', '8', "gray:$tmp/core.raw");
run('magick', "$tmp/guide.png", '-morphology', 'Dilate', 'Disk:16',
    '-depth', '8', "gray:$tmp/envelope.raw");
run('magick', $source, '-depth', '8', "rgb:$tmp/source.raw");
my $rgb = read_bytes("$tmp/source.raw");
my $core = read_bytes("$tmp/core.raw");
my $envelope = read_bytes("$tmp/envelope.raw");
die "Unexpected raw image dimensions" unless length($rgb) == $size * 3
    && length($core) == $size && length($envelope) == $size;

# The AI mask is only a coarse guide. Flood the background up to the original
# dark ink contours, protecting the reliable foreground interior.
my ($barrier, $background, $foreground) = ('', '', '');
my @queue;
for my $i (0 .. $size - 1) {
    my ($r, $g, $b) = map { vec($rgb, 3 * $i + $_, 8) } 0 .. 2;
    my $hi = $r > $g ? $r : $g;
    $hi = $b if $b > $hi;
    my $lo = $r < $g ? $r : $g;
    $lo = $b if $b < $lo;
    vec($barrier, $i, 1) = 1 if $hi < 110 && $hi - $lo < 65;
    if (!vec($envelope, $i, 8)) {
        vec($background, $i, 1) = 1;
        push @queue, $i;
    }
}
# JPEG antialiasing can leave one-pixel gaps in otherwise closed ink contours.
# Seal those gaps before flooding, then remove the added pixel from the matte.
open my $ink, '>:raw', "$tmp/ink.pgm" or die $!;
print {$ink} "P5\n$w $h\n255\n";
for my $i (0 .. $size - 1) {
    print {$ink} vec($barrier, $i, 1) ? "\xff" : "\x00";
}
close $ink;
run('magick', "$tmp/ink.pgm", '-morphology', 'Close', 'Disk:1',
    '-morphology', 'Dilate', 'Disk:1', '-depth', '8', "gray:$tmp/ink.raw");
my $sealed_ink = read_bytes("$tmp/ink.raw");
for my $i (0 .. $size - 1) {
    vec($barrier, $i, 1) = vec($sealed_ink, $i, 8) ? 1 : 0;
}
for (my $head = 0; $head < @queue; ++$head) {
    my $i = $queue[$head];
    my $x = $i % $w;
    my @neighbors;
    push @neighbors, $i - 1 if $x > 0;
    push @neighbors, $i + 1 if $x + 1 < $w;
    push @neighbors, $i - $w if $i >= $w;
    push @neighbors, $i + $w if $i + $w < $size;
    for my $n (@neighbors) {
        next if vec($background, $n, 1) || vec($core, $n, 8)
            || vec($barrier, $n, 1);
        vec($background, $n, 1) = 1;
        push @queue, $n;
    }
}

# Discard detached background islands. Keep only foreground connected to the
# trusted interior; source RGB data is never painted or color corrected.
@queue = ();
for my $i (0 .. $size - 1) {
    if (vec($core, $i, 8)) {
        vec($foreground, $i, 1) = 1;
        push @queue, $i;
    }
}
for (my $head = 0; $head < @queue; ++$head) {
    my $i = $queue[$head];
    my $x = $i % $w;
    my @neighbors;
    push @neighbors, $i - 1 if $x > 0;
    push @neighbors, $i + 1 if $x + 1 < $w;
    push @neighbors, $i - $w if $i >= $w;
    push @neighbors, $i + $w if $i + $w < $size;
    for my $n (@neighbors) {
        next if vec($foreground, $n, 1) || vec($background, $n, 1)
            || !vec($envelope, $n, 8);
        vec($foreground, $n, 1) = 1;
        push @queue, $n;
    }
}
open my $mask, '>:raw', "$tmp/mask.pgm" or die $!;
print {$mask} "P5\n$w $h\n255\n";
for my $i (0 .. $size - 1) {
    print {$mask} vec($foreground, $i, 1) ? "\xff" : "\x00";
}
close $mask;
run('magick', "$tmp/mask.pgm", '-morphology', 'Erode', 'Disk:1',
    '-blur', '0x0.35', '-depth', '8',
    $mask_output);
if ($mask_only) {
    printf "Extracted silhouette mask: %s\n", $mask_output;
    exit 0;
}
run('magick', $source, $mask_output, '-alpha', 'off',
    '-compose', 'CopyOpacity', '-composite', '-depth', '8',
    "$tmp/original_layer.png");
run('magick', "$tmp/original_layer.png", '-resize',
    "${out_w}x${out_h}!", '-depth', '8', "$layers/original_character_layer_wallpaper.png");

# Replace only the previous character silhouette. A broad patch around the new
# silhouette would visibly recolor the already-approved sky along its edges.
run($^X, $0, '--mask-only', $before, "$tmp/previous_mask.png");
run('magick', "$tmp/previous_mask.png", '-morphology', 'Dilate',
    'Disk:1', '-blur', '0x0.35', '-depth', '8', "$tmp/replacement_region.png");
run('magick', $plate, "$tmp/replacement_region.png", '-alpha', 'off',
    '-compose', 'CopyOpacity', '-composite', "$tmp/plate_patch.png");
run('magick', $before, "$tmp/plate_patch.png", '-compose', 'Over', '-composite',
    "$layers/sunset_background_preserved.png");
run('magick', "$layers/sunset_background_preserved.png",
    "$layers/original_character_layer_wallpaper.png", '-compose', 'Over', '-composite',
    '-alpha', 'off', '-depth', '8', $output);
printf "Restored %d original character pixels; output: %s\n", scalar(@queue), $output;
