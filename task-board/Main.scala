//> using scala 3.3.6
//> using dep com.lihaoyi::ujson:4.0.2
import com.sun.net.httpserver.{HttpExchange, HttpServer}
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.util.Try
import ujson.*

object Main:
  private val tasks = mutable.ArrayBuffer.empty[Obj]
  private var nextId = 1
  private def reply(ex: HttpExchange, code: Int, body: Value): Unit =
    val bytes = body.toString.getBytes(UTF_8)
    ex.getResponseHeaders.set("Content-Type", "application/json")
    ex.sendResponseHeaders(code, bytes.length)
    val out = ex.getResponseBody
    try out.write(bytes) finally out.close()
  private def fail(ex: HttpExchange, code: Int, message: String): Unit = reply(ex, code, Obj("error" -> message))
  private def text(obj: Obj, key: String, allowEmpty: Boolean = false): Option[String] =
    obj.value.get(key).collect { case Str(s) if allowEmpty || s.trim.nonEmpty => s }
  private def validKeys(obj: Obj, keys: Set[String]): Boolean = obj.value.keys.forall(keys.contains)
  private def handle(ex: HttpExchange): Unit = synchronized {
    try
      val path = ex.getRequestURI.getPath.split("/").filter(_.nonEmpty).toList
      val method = ex.getRequestMethod
      def body(): Option[Obj] = Try(ujson.read(new String(ex.getRequestBody.readAllBytes(), UTF_8))).toOption.collect { case o: Obj => o }
      (method, path) match
        case ("GET", List("health")) => reply(ex, 200, Obj("status" -> "ok"))
        case ("GET", List("tasks")) => reply(ex, 200, Arr.from(tasks))
        case ("POST", List("tasks")) =>
          body() match
            case Some(o) if validKeys(o, Set("title", "description", "assignee")) && text(o, "title").isDefined &&
                o.value.get("description").forall(_.isInstanceOf[Str]) && o.value.get("assignee").forall(_.isInstanceOf[Str]) =>
              val task = Obj("id" -> Num(nextId), "title" -> o("title"), "description" -> o.value.getOrElse("description", Str("")), "assignee" -> o.value.getOrElse("assignee", Str("")), "status" -> Str("open"), "messages" -> Arr())
              nextId += 1
              tasks += task
              reply(ex, 201, task)
            case _ => fail(ex, 400, "invalid task")
        case (verb, "tasks" :: idText :: rest) if Set("GET", "PATCH", "POST").contains(verb) =>
          val task = Try(idText.toInt).toOption.flatMap(id => tasks.find(_("id").num == id))
          task match
            case None => fail(ex, 404, "task not found")
            case Some(t) => (verb, rest) match
              case ("GET", Nil) => reply(ex, 200, t)
              case ("PATCH", Nil) =>
                body() match
                  case Some(o) if o.value.nonEmpty && validKeys(o, Set("title", "description", "assignee", "status")) &&
                      o.value.get("title").forall(v => v.isInstanceOf[Str] && v.str.trim.nonEmpty) &&
                      o.value.get("description").forall(_.isInstanceOf[Str]) && o.value.get("assignee").forall(_.isInstanceOf[Str]) &&
                      o.value.get("status").forall(v => v.isInstanceOf[Str] && Set("open", "in_progress", "done").contains(v.str)) =>
                        o.value.foreach { case (k, v) => t(k) = v }
                        reply(ex, 200, t)
                  case _ => fail(ex, 400, "invalid update")
              case ("POST", List("messages")) =>
                body() match
                  case Some(o) if validKeys(o, Set("author", "text")) && text(o, "author").isDefined && text(o, "text").isDefined =>
                    val msg = Obj("author" -> o("author"), "text" -> o("text"))
                    t("messages").arr += msg
                    reply(ex, 201, msg)
                  case _ => fail(ex, 400, "invalid message")
              case _ => fail(ex, 404, "not found")
        case _ => fail(ex, 404, "not found")
    catch case _: Exception => fail(ex, 500, "internal error")
    finally ex.close()
  }
  def main(args: Array[String]): Unit =
    val port = sys.env.getOrElse("PORT", "8082").toInt
    val server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0)
    server.createContext("/", (ex: HttpExchange) => handle(ex))
    server.start()
    println(s"Task board listening on 0.0.0.0:$port")
