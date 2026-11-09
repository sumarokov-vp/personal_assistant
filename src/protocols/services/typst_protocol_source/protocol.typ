#import "@local/smartist:1.0.0": smartist
#show: smartist.with(
  title: "{{document_title}}",
  subtitle: [{{subtitle}}],
  author: "Smartist LLC",
  date: "{{date}}",
)

{{body}}
