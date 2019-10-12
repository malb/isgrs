When:   {{event.datetime.strftime("%a, %d %b %Y %H:%M")}}
Where:  {{event.venue}}
Who:    {{event.speaker}} {% if event.speaker_affiliation %}({{event.speaker_affiliation}}){% endif %}

# Title #

{{event.title}}

# Abstract #

{{event.abstract}}

# Bio #

{{event.speaker_bio}}

Cheers,
{{signers}}
